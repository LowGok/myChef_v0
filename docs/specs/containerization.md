---
status: draft
status_description: "Delivery components inspected; awaiting independent spec review and owner acceptance."
issue: null
goal: "MyChef runs from a verified nonroot container and releases through the shared container action."
covers:
  - Dockerfile
  - .dockerignore
  - compose.yaml
  - .github/workflows/container-release.yml
  - scripts/stage_python_runtime.py
  - tests/container/
  - pyproject.toml
  - uv.lock
  - .streamlit/config.toml
  - mychefApp/
  - img/
  - README.md
---

# MyChef container runtime and publication

## Context

Land [dependency maintenance PR 2](https://github.com/LowGok/myChef_v0/pull/2)
before building the application image. That change pins Python 3.15.2, uv 0.13.5
and the application dependencies, and verifies the live menu flow
(`76837f7:pyproject.toml`; `76837f7:uv.lock`; PR 2 validation).
The application needs its working directory to contain `img/` and
`.streamlit/` (`mychefApp/main.py:20`; `mychefApp/displayMeals.py:25`). PostgreSQL,
Gemini and Cloudinary remain external services.

The pinned [container conventions](https://github.com/vhco-pro/docs/blob/e4d58d2cd69bd42f1efacf91dfdd3f01a24e134a/conventions/containers.md)
require a distroless Python runtime, nonroot execution and digest-pinned inputs.
The [shared release action](https://github.com/michielvha/docker-release-action/blob/c499e52a1a05e5bdd8cf03ba19a423d4c7ec25e3/action.yaml)
builds and pushes images, then applies its enabled security controls. Its default
mode has no build-only switch. Several nested actions still use moving major
references; those references need hardening in the shared component before this
release path can be described as immutable.

## Scope

Package the Streamlit application, provide a local container run configuration,
verify the final runtime, and prepare explicit GHCR publication through the
shared action. Keep the database external and pass service credentials only at
runtime. Dependency maintenance must land first.

Database migrations, Kubernetes deployment, a new reverse proxy, automatic
production deployment and changes to the ORM proposal are outside this feature.

## Design

Use a multi-stage Dockerfile. The builder starts from the verified
`python:3.15.2-slim-trixie@sha256:96c27ba7394e245a1dd0830089037a57dffbe25b51d2bfdd2feef89194ee934f`.
Install the exact uv version declared by `pyproject.toml`; verify its downloaded
artifact, then install runtime dependencies with `uv sync --locked --no-dev`.
Keep dependency layers separate from application source layers.

Stage the interpreter, standard library, runtime dependencies and shared
libraries into `gcr.io/distroless/cc-debian13:nonroot`. Resolve and commit that
runtime's actual digest before implementation; a family name is not a build
pin. Inspect the interpreter and every native extension with `ldd`, including
Psycopg, NumPy, PyArrow and Pillow. Verify the actual final image rather than
assuming that matching Debian families proves ABI compatibility. Remove pip,
ensurepip, uv, their metadata, development dependencies and build tools.

Use `/app` as the working directory, `USER nonroot:nonroot` (65532), and an
exec-form Python entry point invoking Streamlit on `0.0.0.0:8501`. Disable
bytecode writes, file watching and usage telemetry. Keep CORS and XSRF protection
enabled. Allowlist only the Dockerfile, manifests, staging script, application,
image assets and `.streamlit/config.toml` in `.dockerignore`; credentials,
Git history, tests and local artifacts must stay outside the build context.

The local Compose service uses a read-only root, drops capabilities and enables
`no-new-privileges`. Supply bounded writable tmpfs mounts for `/tmp` and
Streamlit's user configuration directory if the runtime checks establish that
it needs writes there. Mount `.streamlit/secrets.toml` read-only at
`/app/.streamlit/secrets.toml`. Bind mounts preserve host ownership, so the
operator must grant the container UID read access; do not make credentials
world-readable. No database password or API key enters a build argument, image
environment setting, image layer or repository file.

Publish the local port on `127.0.0.1:8501`. The existing private Tailscale Serve
mapping can keep forwarding HTTPS and WebSockets to that port. This avoids
reconfiguring the tailnet or enabling public Funnel access.

Start with a tested `linux/amd64` image. Publication uses
`michielvha/docker-release-action` at an inspected full SHA. The inspected
`c499e52a1a05e5bdd8cf03ba19a423d4c7ec25e3` is the contract baseline; review a
replacement that pins its nested action references before selecting the release
revision. The caller sets registry `ghcr.io`, lowercase namespace `lowgok`,
project `mychef_v0`, and an explicit exact version supplied by one version owner.
Do not use the action's default `dev` version or derive competing versions.
Confirm that the caller token can publish the intended package and configure
package visibility before the first authorized publication.

Set `trivy-scan: 'true'`, `trivy-severity: 'HIGH,CRITICAL'`,
`trivy-exit-code: '1'`, `cosign-sign: 'true'`, `sbom: 'true'`,
`attest-provenance: 'true'` and `attest-sbom: 'true'` explicitly. Grant the job
`contents: read`, `packages: write`, `id-token: write` and `attestations: write`;
SARIF also needs `security-events: write`. PR checks must not publish images or
tags. Local Docker builds and runtime smoke checks do not call the action's
publication mode. Serialize publication and record the final `release-digest`.

The action scans after pushing and also publishes a `latest` alias. A pushed
tag alone is not evidence of a successful release. Consumers use the final
digest only after the scan, signature, attestations and final-image runtime
checks pass. Multi-platform publication requires testing each platform and
applying the same controls to the merged image index; it is a later extension.

## Acceptance Criteria

- [ ] AC-01: The final image starts as UID 65532 with a read-only root and serves the login page, health endpoint and Streamlit WebSocket connection.
- [ ] AC-02: Runtime dependencies install from the committed uv lock and the final image contains no credentials, package installers, shell, compiler or development test tools.
- [ ] AC-03: An explicit live browser run against the container saves a new meal and its ingredients, displays the matching recipe, and handles unavailable image quota visibly.
- [ ] AC-04: Authorized publication uses the inspected shared action with all required security controls, and consumers can verify its signature, SBOM and provenance against the recorded final digest.
- [ ] AC-05: PR checks leave registries and Git tags unchanged, and local startup preserves CORS, XSRF and private tailnet forwarding.

## Test Plan

| Criterion | Proof |
| --- | --- |
| AC-01 | Build the final image; inspect its user; start with read-only root and documented tmpfs mounts; verify HTTP health, a browser-rendered login page, WebSocket upgrade and graceful termination. |
| AC-02 | Check uv lock freshness; inspect the build context and final filesystem; import required native modules and verify development tools and secret files are absent. |
| AC-03 | Extend the existing live browser harness to target a running container; compare that generation's exact meal ID and ingredients with the test account's stored data. |
| AC-04 | Inspect the selected shared action and transitive refs; run an explicitly authorized release; verify Trivy result, Cosign identity and digest-bound attestations for its release-digest. |
| AC-05 | Validate workflow triggers and permissions; observe a PR check without publication; repeat HTTPS browser and WebSocket smoke checks through the existing tailnet URL. |

## Tasks

- [ ] T1 `tests/container/` - add observable runtime checks; they fail while the image is absent (AC-01, AC-02, AC-05).
- [ ] T2 `Dockerfile`, `.dockerignore`, `scripts/stage_python_runtime.py` - pin verified inputs and stage the minimal runtime; native imports and T1 pass (AC-01, AC-02).
- [ ] T3 `compose.yaml`, `README.md` - document secrets ownership and writable paths; local startup and tailnet checks pass (AC-01, AC-05).
- [ ] T4 `tests/container/` - connect the live menu harness to the running image; exact generated content is displayed and persisted (AC-03).
- [ ] T5 `.github/workflows/container-release.yml` - select the hardened shared action and exact-version source; workflow validation passes and an authorized release meets the verification procedure (AC-04, AC-05).

## Open Questions

None. The shared action's transitive pinning is an implementation prerequisite;
publication and deployment still require their own explicit authorization.

## Review Log

| Date | Review | Kind | Commit | Model | Isolation | Outcome |
| --- | --- | --- | --- | --- | --- | --- |

No independent review or owner acceptance has occurred. The feature remains draft.

## Sources

- [Pinned container conventions](https://github.com/vhco-pro/docs/blob/e4d58d2cd69bd42f1efacf91dfdd3f01a24e134a/conventions/containers.md): distroless runtime, digest pins, nonroot execution and allowlisted context.
- [Pinned container security profile](https://github.com/vhco-pro/docs/blob/e4d58d2cd69bd42f1efacf91dfdd3f01a24e134a/knowledge/container-release.md): required controls, permissions, post-push scan and transitive action limitations.
- [Shared action implementation](https://github.com/michielvha/docker-release-action/blob/c499e52a1a05e5bdd8cf03ba19a423d4c7ec25e3/action.yaml): namespace inputs, publication modes, release-digest and enabled controls.
- [uv locked synchronization](https://docs.astral.sh/uv/concepts/projects/sync/): locked installation and development group exclusion.
