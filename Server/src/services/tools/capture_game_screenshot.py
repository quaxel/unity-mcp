from typing import Annotated, Any

from fastmcp import Context
from fastmcp.server.server import ToolResult
from mcp.types import ToolAnnotations

from services.registry import mcp_for_unity_tool
from services.tools import get_unity_instance_from_context
from services.tools.manage_scene import _extract_images
from services.tools.preflight import preflight
from services.tools.utils import coerce_bool, coerce_int
from transport.legacy.unity_connection import async_send_command_with_retry
from transport.unity_transport import send_with_unity_instance


@mcp_for_unity_tool(
    unity_target="manage_scene",
    description=(
        "Captures a screenshot from the Unity Game view and returns it inline for sharing. "
        "Defaults to include_image=true so the response contains an image block."
    ),
    annotations=ToolAnnotations(
        title="Capture Game Screenshot",
    ),
)
async def capture_game_screenshot(
    ctx: Context,
    camera: Annotated[str, "Optional camera reference (name/path/instance ID). Defaults to Camera.main."] | None = None,
    include_image: Annotated[bool | str, "Return inline base64 PNG image. Default true."] = True,
    max_resolution: Annotated[int | str, "Longest edge for inline image in pixels. Default 640."] = 640,
    screenshot_file_name: Annotated[str, "Optional screenshot filename in Assets/Screenshots."] | None = None,
    screenshot_super_size: Annotated[int | str, "Screenshot supersize multiplier (integer >= 1)."] | None = None,
) -> dict[str, Any] | ToolResult:
    unity_instance = get_unity_instance_from_context(ctx)

    gate = await preflight(ctx, wait_for_no_compile=True, refresh_if_dirty=True)
    if gate is not None:
        return gate.model_dump()

    coerced_include_image = coerce_bool(include_image, default=True)
    coerced_max_resolution = coerce_int(max_resolution, default=640)
    coerced_super_size = coerce_int(screenshot_super_size, default=None)

    if coerced_max_resolution is None or coerced_max_resolution <= 0:
        return {"success": False, "message": "max_resolution must be a positive integer greater than zero."}

    params: dict[str, Any] = {
        "action": "screenshot",
        "includeImage": coerced_include_image,
        "maxResolution": coerced_max_resolution,
    }
    if camera:
        params["camera"] = camera
    if screenshot_file_name:
        params["fileName"] = screenshot_file_name
    if coerced_super_size is not None:
        params["superSize"] = coerced_super_size

    try:
        response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "manage_scene",
            params,
        )

        if isinstance(response, dict) and response.get("success"):
            image_result = _extract_images(response, "screenshot")
            if image_result is not None:
                return image_result
            return {
                "success": True,
                "message": response.get("message", "Game screenshot captured."),
                "data": response.get("data"),
            }

        return response if isinstance(response, dict) else {"success": False, "message": str(response)}
    except Exception as e:
        return {"success": False, "message": f"Python error capturing game screenshot: {str(e)}"}
