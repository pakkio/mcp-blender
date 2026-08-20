import json

from mcp_blender.config import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    ENV_HOST,
    ENV_PORT,
    resolve_host_port,
    settings_path,
)


def test_settings_path_is_under_home(tmp_path):
    path = settings_path(home=tmp_path)
    assert path == tmp_path / ".mcp-blender" / "settings.json"


def test_default_when_nothing_present(tmp_path, monkeypatch):
    monkeypatch.delenv(ENV_HOST, raising=False)
    monkeypatch.delenv(ENV_PORT, raising=False)
    host, port = resolve_host_port(home=tmp_path)
    assert (host, port) == (DEFAULT_HOST, DEFAULT_PORT)


def test_settings_file_overrides_default(tmp_path, monkeypatch):
    monkeypatch.delenv(ENV_HOST, raising=False)
    monkeypatch.delenv(ENV_PORT, raising=False)
    path = settings_path(home=tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"host": "10.0.0.5", "port": 12345}))

    host, port = resolve_host_port(home=tmp_path)
    assert (host, port) == ("10.0.0.5", 12345)


def test_env_var_overrides_settings_file(tmp_path, monkeypatch):
    path = settings_path(home=tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"host": "10.0.0.5", "port": 12345}))

    monkeypatch.setenv(ENV_HOST, "192.168.1.1")
    monkeypatch.setenv(ENV_PORT, "9999")

    host, port = resolve_host_port(home=tmp_path)
    assert (host, port) == ("192.168.1.1", 9999)


def test_corrupt_settings_file_falls_back_to_default(tmp_path, monkeypatch):
    monkeypatch.delenv(ENV_HOST, raising=False)
    monkeypatch.delenv(ENV_PORT, raising=False)
    path = settings_path(home=tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text("not json")

    host, port = resolve_host_port(home=tmp_path)
    assert (host, port) == (DEFAULT_HOST, DEFAULT_PORT)
