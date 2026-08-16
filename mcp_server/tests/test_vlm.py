import httpx
import pytest

from mcp_blender_pakkio.vlm import VLMError, critique_image, is_configured, resolve_model


def test_is_configured_false_without_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    assert is_configured() is False


def test_is_configured_true_with_key(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    assert is_configured() is True


def test_resolve_model_uses_override():
    assert resolve_model("my/model") == "my/model"


def test_resolve_model_uses_env(monkeypatch):
    monkeypatch.setenv("OPENROUTER_VISION_MODEL", "vendor/model-x")
    assert resolve_model(None) == "vendor/model-x"


def test_resolve_model_falls_back_to_default(monkeypatch):
    monkeypatch.delenv("OPENROUTER_VISION_MODEL", raising=False)
    assert resolve_model(None)


@pytest.mark.asyncio
async def test_critique_image_without_key_raises(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(VLMError, match="OPENROUTER_API_KEY"):
        await critique_image("is this consistent?", b"fake-png")


@pytest.mark.asyncio
async def test_critique_image_happy_path(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")

    async def fake_post(self, url, headers=None, json=None):
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "Looks period-accurate."}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 20},
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    result = await critique_image("is this consistent?", b"fake-png")

    assert result["critique"] == "Looks period-accurate."
    assert result["prompt_tokens"] == 100


@pytest.mark.asyncio
async def test_critique_image_non_200_raises(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")

    async def fake_post(self, url, headers=None, json=None):
        return httpx.Response(402, text="insufficient credits", request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    with pytest.raises(VLMError, match="402"):
        await critique_image("q", b"fake-png")
