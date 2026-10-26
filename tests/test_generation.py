import json
from types import SimpleNamespace
from unittest.mock import Mock

import generationTrace
import recipeGenerator
import imageGenerator


def test_real_request_builder_records_provider_output_without_api_key(monkeypatch, tmp_path):
    monkeypatch.setenv("MYCHEF_TRACE_DIR", str(tmp_path))
    monkeypatch.setattr(recipeGenerator.st, "secrets", {"gemini_api_key": "private-api-key"})
    client = Mock()
    response = json.dumps({"recipes": [{"Recipe Title": "Soup"}]})
    client.models.generate_content.return_value = SimpleNamespace(text=response)
    monkeypatch.setattr(recipeGenerator.genai, "Client", Mock(return_value=client))
    assert recipeGenerator.gemini_ai_api("Number of recipes: 1", 4) == response
    request = client.models.generate_content.call_args.kwargs
    assert request["model"] == "gemini-3.8-flash"
    assert request["config"].temperature == 0.5
    assert request["config"].response_mime_type == "application/json"
    assert request["config"].response_schema.properties["recipes"]
    request_file = next(tmp_path.glob("*/request.json"))
    assert json.loads(request_file.read_text())["prompt"] == "Number of recipes: 1"
    assert (request_file.parent / "response.txt").read_text() == response
    assert "private-api-key" not in "".join(p.read_text() for p in request_file.parent.iterdir())


def test_trace_errors_do_not_include_exception_urls_or_keys(monkeypatch, tmp_path):
    monkeypatch.setenv("MYCHEF_TRACE_DIR", str(tmp_path))
    path = generationTrace.start_trace("model", "prompt", "instructions", 0.5)
    generationTrace.finish_trace(path, error=RuntimeError("https://provider?key=private-api-key"))
    assert json.loads((path / "error.json").read_text()) == {"error_type": "RuntimeError", "status_code": None}


def test_image_generation_uses_supported_content_api(monkeypatch):
    monkeypatch.setattr(imageGenerator.st, "secrets", {"gemini_api_key": "private-api-key"})
    client = Mock()
    client.models.generate_content.return_value = SimpleNamespace(candidates=[SimpleNamespace(
        content=SimpleNamespace(parts=[SimpleNamespace(inline_data=SimpleNamespace(data=b"image-bytes"))]))])
    monkeypatch.setattr(imageGenerator.genai, "Client", Mock(return_value=client))
    assert imageGenerator.imageGenerator("Carrot soup", "carrots") == b"image-bytes"
    args = client.models.generate_content.call_args.kwargs
    assert args["model"] == "gemini-3.1-flash-image"
    assert "Carrot soup" in args["contents"]
    client.models.generate_images.assert_not_called()
