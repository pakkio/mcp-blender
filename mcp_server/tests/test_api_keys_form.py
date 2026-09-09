"""set_api_keys without hand-editing .env: server config persistence + tool."""

import importlib.util
import json
from pathlib import Path
from unittest.mock import AsyncMock

from conftest import FakeMCP
from mcp_blender import config as server_config
from mcp_blender.tools.env_info_ops import register_env_info_tools

REPO_ROOT = Path(__file__).resolve().parents[2]
EXT_CONFIG = REPO_ROOT / "extension" / "config.py"


def _load_extension_config():
    spec = importlib.util.spec_from_file_location("ext_config_under_test", EXT_CONFIG)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_managed_keys_stay_in_sync():
    ext = _load_extension_config()
    assert tuple(server_config.MANAGED_KEYS) == tuple(ext.MANAGED_KEYS)


def test_save_env_keys_writes_and_applies(tmp_path, monkeypatch):
    for k in server_config.MANAGED_KEYS:
        monkeypatch.delenv(k, raising=False)
    path = server_config.save_env_keys(
        {"OPENROUTER_API_KEY": "sk-test-1234567890", "MESHY_API_KEY": ""},
        home=tmp_path,
    )
    assert path == tmp_path / ".mcp-blender" / ".env"
    text = path.read_text(encoding="utf-8")
    assert "OPENROUTER_API_KEY=sk-test-1234567890" in text
    assert "MESHY_API_KEY" not in text
    import os

    assert os.environ["OPENROUTER_API_KEY"] == "sk-test-1234567890"
    assert "MESHY_API_KEY" not in os.environ


def test_save_env_keys_preserves_unrelated_lines(tmp_path, monkeypatch):
    for k in server_config.MANAGED_KEYS:
        monkeypatch.delenv(k, raising=False)
    target = tmp_path / ".mcp-blender" / ".env"
    target.parent.mkdir(parents=True)
    target.write_text("# comment\nOTHER_THING=keepme\nOPENROUTER_API_KEY=oldvalue12345678\n", encoding="utf-8")
    server_config.save_env_keys({"OPENROUTER_API_KEY": "newvalue-1234567890"}, home=tmp_path)
    text = target.read_text(encoding="utf-8")
    assert "# comment" in text
    assert "OTHER_THING=keepme" in text
    assert "newvalue-1234567890" in text
    assert "oldvalue" not in text


def test_save_env_keys_empty_removes_line(tmp_path, monkeypatch):
    monkeypatch.setenv("TRIPO_API_KEY", "todelete-12345678")
    target = tmp_path / ".mcp-blender" / ".env"
    target.parent.mkdir(parents=True)
    target.write_text("TRIPO_API_KEY=todelete-12345678\n", encoding="utf-8")
    server_config.save_env_keys({"TRIPO_API_KEY": ""}, home=tmp_path)
    import os

    assert "TRIPO_API_KEY" not in target.read_text(encoding="utf-8")
    assert "TRIPO_API_KEY" not in os.environ


async def test_set_api_keys_tool_sets_and_masks(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    for k in server_config.MANAGED_KEYS:
        monkeypatch.delenv(k, raising=False)

    mcp = FakeMCP()
    bridge = AsyncMock()
    bridge.send_request.return_value = {"success": True}
    register_env_info_tools(mcp, bridge)

    assert "set_api_keys" in mcp.tools
    secret = "sk-live-key-abcdefgh1234567890"
    result = await mcp.tools["set_api_keys"](OPENROUTER_API_KEY=secret)

    assert result["success"] is True
    assert result["updated"] == ["OPENROUTER_API_KEY"]
    assert (tmp_path / ".mcp-blender" / ".env").exists()
    dumped = json.dumps(result)
    assert secret not in dumped  # never echo full secrets back
    assert result["info"]["keys"]["OPENROUTER_API_KEY"]["masked"] == "sk-...890"
    bridge.send_request.assert_called_once()  # live-propagated to Blender
    assert result["blender_live"] is True


async def test_set_api_keys_tool_offline_blender_still_succeeds(tmp_path, monkeypatch):
    from mcp_blender.errors import BridgeError, ErrorType

    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    for k in server_config.MANAGED_KEYS:
        monkeypatch.delenv(k, raising=False)

    mcp = FakeMCP()
    bridge = AsyncMock()
    bridge.send_request.side_effect = BridgeError(ErrorType.CONNECTION, "Not connected")
    register_env_info_tools(mcp, bridge)

    result = await mcp.tools["set_api_keys"](MESHY_API_KEY="msy-key-1234567890abcdef")
    assert result["success"] is True
    assert result["blender_live"] is False
    assert "offline" in result["message"]


async def test_set_api_keys_empty_clears_and_noop_errors(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    for k in server_config.MANAGED_KEYS:
        monkeypatch.delenv(k, raising=False)

    mcp = FakeMCP()
    bridge = AsyncMock()
    register_env_info_tools(mcp, bridge)

    monkeypatch.setenv("TRIPO_API_KEY", "tripo-to-clear-12345678")
    result = await mcp.tools["set_api_keys"](TRIPO_API_KEY="")
    assert result["success"] is True
    assert result["cleared"] == ["TRIPO_API_KEY"]

    result = await mcp.tools["set_api_keys"]()
    assert result["success"] is False
    assert "No keys provided" in result["message"]


def test_extension_config_save_roundtrip(tmp_path, monkeypatch):
    ext = _load_extension_config()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    import os

    for k in ext.MANAGED_KEYS:
        os.environ.pop(k, None)
        monkeypatch.delenv(k, raising=False)
    path = ext.save_managed_keys({"OPENROUTER_API_KEY": "ext-key-1234567890", "HF_TOKEN": ""})
    assert path == tmp_path / ".mcp-blender" / ".env"
    assert os.environ["OPENROUTER_API_KEY"] == "ext-key-1234567890"
    assert ext.read_managed_keys()["OPENROUTER_API_KEY"] == "ext-key-1234567890"
