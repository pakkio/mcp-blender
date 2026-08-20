import base64

from mcp.server.fastmcp import Image

from mcp_blender.images import image_result


def test_passthrough_when_key_missing():
    result = {"success": True, "output_path": "/tmp/x.png"}
    assert image_result(result) is result


def test_passthrough_when_key_empty():
    result = {"success": True, "image_base64": None}
    assert image_result(result) is result


def test_decodes_plain_base64():
    raw = b"png-bytes"
    result = {"success": True, "output_path": "/tmp/x.png", "image_base64": base64.b64encode(raw).decode()}

    converted = image_result(result)

    assert isinstance(converted, list)
    assert isinstance(converted[0], Image)
    assert converted[0].data == raw
    assert converted[1] == {"success": True, "output_path": "/tmp/x.png"}


def test_decodes_data_uri_with_custom_key():
    raw = b"png-bytes"
    uri = "data:image/png;base64," + base64.b64encode(raw).decode()
    result = {"success": True, "base64_data_uri": uri}

    converted = image_result(result, "base64_data_uri")

    assert converted[0].data == raw
    assert "base64_data_uri" not in converted[1]


def test_invalid_base64_falls_back_to_dict():
    result = {"success": True, "image_base64": "@@@not-base64@@@"}
    assert image_result(result) is result
