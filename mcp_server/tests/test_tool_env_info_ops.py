import json
from unittest.mock import AsyncMock

from conftest import FakeMCP
from mcp_blender.tools import register_all_tools
from mcp_blender.tools.env_info_ops import mask_secret, register_env_info_tools


def test_mask_secret_first3_last3():
    assert mask_secret("sk-or-v1-abcdefgh1234567890") == "sk-...890"
    assert mask_secret("12345678") == "123...678"


def test_mask_secret_short_values_fully_masked():
    assert mask_secret("") == "***"
    assert mask_secret("abc") == "***"
    assert mask_secret("1234567") == "***"


async def test_get_env_info_registration_and_output(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-value-12345678")

    mcp = FakeMCP()
    bridge = AsyncMock()

    register_env_info_tools(mcp, bridge)
    assert "get_env_info" in mcp.tools

    result = await mcp.tools["get_env_info"]()

    assert result["success"] is True
    assert result["python"]["executable"]
    assert isinstance(result["python"]["in_venv"], bool)
    assert len(result["env_files"]) == 2
    assert all("path" in entry and "exists" in entry for entry in result["env_files"])
    assert set(result["keys"]["OPENROUTER_API_KEY"]) == {"masked", "source"}


async def test_get_env_info_never_leaks_full_secrets(monkeypatch):
    long_secret = "super-secret-api-key-value-9999"
    short_secret = "tiny"

    monkeypatch.setenv("MESHY_API_KEY", long_secret)
    monkeypatch.setenv("SOME_CUSTOM_TOKEN", short_secret)

    mcp = FakeMCP()
    bridge = AsyncMock()
    register_env_info_tools(mcp, bridge)

    result = await mcp.tools["get_env_info"]()
    dumped = json.dumps(result)

    assert long_secret not in dumped
    assert short_secret not in dumped
    assert result["keys"]["MESHY_API_KEY"]["masked"] == "sup...999"
    assert result["keys"]["SOME_CUSTOM_TOKEN"]["masked"] == "***"
    assert result["keys"]["SOME_CUSTOM_TOKEN"]["source"] == "environment"


async def test_public_config_keys_returned_unmasked(monkeypatch):
    monkeypatch.setenv("OPENROUTER_VISION_MODEL", "google/gemini-2.5-flash-lite")

    mcp = FakeMCP()
    bridge = AsyncMock()
    register_env_info_tools(mcp, bridge)

    result = await mcp.tools["get_env_info"]()

    assert result["keys"]["OPENROUTER_VISION_MODEL"]["masked"] == "google/gemini-2.5-flash-lite"


async def test_null_or_empty_keys_are_cancelled_with_strikethrough(monkeypatch):
    monkeypatch.delenv("TRELLIS_API_KEY", raising=False)
    monkeypatch.setenv("EMPTY_TOKEN_XYZ", "")

    mcp = FakeMCP()
    bridge = AsyncMock()
    register_env_info_tools(mcp, bridge)

    result = await mcp.tools["get_env_info"]()

    cancelled = result["keys"]["~~TRELLIS_API_KEY~~"]
    assert cancelled["masked"] == "cancelled"
    assert "TRELLIS_API_KEY" not in result["keys"]

    empty = result["keys"]["~~EMPTY_TOKEN_XYZ~~"]
    assert empty["masked"] == "cancelled"
    assert "cancelled" in json.dumps(result)


async def test_source_path_from_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text('OPENROUTER_API_KEY="abcdefgh12345678"\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENROUTER_API_KEY", "abcdefgh12345678")

    mcp = FakeMCP()
    bridge = AsyncMock()
    register_env_info_tools(mcp, bridge)

    result = await mcp.tools["get_env_info"]()

    entry = result["keys"]["OPENROUTER_API_KEY"]
    assert entry["masked"] == "abc...678"
    assert entry["source"] == str(env_file)


async def test_key_declared_only_in_file_shows_cancelled_with_source(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("TRIPO_API_KEY=\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("TRIPO_API_KEY", raising=False)

    mcp = FakeMCP()
    bridge = AsyncMock()
    register_env_info_tools(mcp, bridge)

    result = await mcp.tools["get_env_info"]()

    entry = result["keys"]["~~TRIPO_API_KEY~~"]
    assert entry["masked"] == "cancelled"
    assert entry["source"] == str(env_file)


def test_registered_via_register_all_tools(monkeypatch):
    monkeypatch.setenv("MCP_BLENDER_TOOL_MODE", "FULL")
    mcp = FakeMCP()
    bridge = AsyncMock()

    register_all_tools(mcp, bridge)

    assert "get_env_info" in mcp.tools


def test_available_in_default_aggregated_mode():
    mcp = FakeMCP()
    bridge = AsyncMock()

    register_all_tools(mcp, bridge)

    assert "get_env_info" in mcp.tools
