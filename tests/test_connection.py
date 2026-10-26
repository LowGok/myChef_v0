from unittest.mock import Mock

import pytest
from sqlalchemy.exc import IntegrityError, OperationalError

import connection


def operation_mock(**kwargs):
    operation = Mock(**kwargs)
    operation.__name__ = "operation"
    return operation


@pytest.fixture(autouse=True)
def isolate_streamlit(monkeypatch):
    monkeypatch.setattr(connection.st, "error", Mock())
    monkeypatch.setattr(connection.time, "sleep", Mock())
    monkeypatch.setattr(connection, "reset_connection", Mock())


def disconnect():
    return OperationalError("INSERT private data", {"password": "secret"},
                            Exception("SSL SYSCALL error: EOF detected"),
                            connection_invalidated=True)


def test_write_is_not_replayed_when_commit_outcome_is_unknown():
    operation = operation_mock(side_effect=disconnect())
    assert connection.with_db_retry()(operation)() is None
    assert operation.call_count == 1
    connection.time.sleep.assert_not_called()


def test_programming_errors_propagate():
    @connection.with_db_retry()
    def operation():
        raise ValueError("invalid recipe")

    with pytest.raises(ValueError, match="invalid recipe"):
        operation()
    connection.st.error.assert_not_called()
    connection.reset_connection.assert_not_called()


def test_operational_errors_are_not_all_transient():
    error = OperationalError("SELECT 1", {}, Exception("password authentication failed"))
    assert not connection.is_transient_db_error(error)
    assert not connection.is_transient_db_error(ValueError("broken pipe"))
    assert connection.is_transient_db_error(disconnect())


def test_database_error_does_not_print_query_parameters(capsys):
    operation = operation_mock(side_effect=IntegrityError("INSERT", {"password": "secret"},
                                               Exception("duplicate email")))
    connection.with_db_retry()(operation)()
    captured = capsys.readouterr()
    assert "secret" not in captured.out + captured.err
    connection.reset_connection.assert_not_called()


def test_read_only_operation_retries_disconnects():
    operation = operation_mock(side_effect=[disconnect(), disconnect(), "ok"])
    assert connection.with_db_retry(read_only=True)(operation)() == "ok"
    assert operation.call_count == 3
    assert [call.args[0] for call in connection.time.sleep.call_args_list] == [1.0, 2.0]


def test_read_retries_are_bounded():
    operation = operation_mock(side_effect=disconnect())
    assert connection.with_db_retry(read_only=True)(operation)() is None
    assert operation.call_count == 3
    connection.st.error.assert_called_once()


def test_pool_checks_remain_enabled(monkeypatch):
    connect = Mock()
    monkeypatch.setattr(connection.st, "connection", connect)
    connection.init_connection()
    assert connect.call_args.kwargs["pool_pre_ping"] is True
    assert connect.call_args.kwargs["pool_recycle"] == 180


def test_invalid_retry_count_is_rejected():
    with pytest.raises(ValueError):
        connection.with_db_retry(max_retries=0)
