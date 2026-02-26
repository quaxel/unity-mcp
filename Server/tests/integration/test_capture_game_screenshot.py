import asyncio

from fastmcp.server.server import ToolResult

from .test_helpers import DummyContext
import services.tools.capture_game_screenshot as capture_game_screenshot_mod


def test_capture_game_screenshot_defaults_and_image_tool_result(monkeypatch):
    captured = {}

    async def fake_async_send(cmd, params, **kwargs):
        captured["params"] = params
        return {
            "success": True,
            "message": "ok",
            "data": {
                "path": "Assets/Screenshots/shot.png",
                "imageBase64": "iVBOR_FAKE",
                "imageWidth": 640,
                "imageHeight": 360,
            },
        }

    monkeypatch.setattr(capture_game_screenshot_mod, "async_send_command_with_retry", fake_async_send)

    result = asyncio.run(
        capture_game_screenshot_mod.capture_game_screenshot(
            ctx=DummyContext(),
        )
    )

    assert isinstance(result, ToolResult)
    assert len(result.content) == 2
    assert result.content[1].type == "image"
    assert result.content[1].data == "iVBOR_FAKE"

    params = captured["params"]
    assert params["action"] == "screenshot"
    assert params["includeImage"] is True
    assert params["maxResolution"] == 640


def test_capture_game_screenshot_forwards_camera_and_coerces(monkeypatch):
    captured = {}

    async def fake_async_send(cmd, params, **kwargs):
        captured["params"] = params
        return {"success": True, "message": "ok", "data": {"path": "Assets/Screenshots/custom.png"}}

    monkeypatch.setattr(capture_game_screenshot_mod, "async_send_command_with_retry", fake_async_send)

    result = asyncio.run(
        capture_game_screenshot_mod.capture_game_screenshot(
            ctx=DummyContext(),
            camera="MainCamera",
            include_image="false",
            max_resolution="256",
            screenshot_super_size="2",
            screenshot_file_name="custom",
        )
    )

    assert isinstance(result, dict)
    assert result["success"] is True
    assert result["data"]["path"] == "Assets/Screenshots/custom.png"

    params = captured["params"]
    assert params["camera"] == "MainCamera"
    assert params["includeImage"] is False
    assert params["maxResolution"] == 256
    assert params["superSize"] == 2
    assert params["fileName"] == "custom"


def test_capture_game_screenshot_rejects_invalid_max_resolution(monkeypatch):
    called = {"value": False}

    async def fake_async_send(cmd, params, **kwargs):
        called["value"] = True
        return {"success": True}

    monkeypatch.setattr(capture_game_screenshot_mod, "async_send_command_with_retry", fake_async_send)

    result = asyncio.run(
        capture_game_screenshot_mod.capture_game_screenshot(
            ctx=DummyContext(),
            max_resolution=0,
        )
    )

    assert result["success"] is False
    assert "max_resolution must be a positive integer" in result["message"]
    assert called["value"] is False
