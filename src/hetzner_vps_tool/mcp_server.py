"""Four MCP tools exposed over stdio."""

from mcp.server.fastmcp import FastMCP

from .client import get_client
from . import tools

mcp = FastMCP("hetzner-vps-tool")


@mcp.tool()
def list_servers() -> list[dict]:
    """Liệt kê toàn bộ VPS trong project Hetzner Cloud."""
    return tools.list_servers(get_client())


@mcp.tool()
def manage_server(
    action: str, name: str | None = None, server_type: str | None = None,
    image: str | int | None = None, location: str | None = None,
    server_id: int | None = None, server_name: str | None = None,
) -> dict:
    """Tạo VPS ở location hoặc xóa VPS theo ID/tên."""
    return tools.manage_server(
        get_client(), action, name=name, server_type=server_type,
        image=image, location=location, server_id=server_id,
        server_name=server_name,
    )


@mcp.tool()
def manage_snapshot(
    action: str, server_id: int | None = None,
    description: str | None = None, image_id: int | None = None,
) -> dict:
    """Tạo, restore hoặc xóa snapshot; restore ghi đè ổ đĩa VPS."""
    return tools.manage_snapshot(
        get_client(), action, server_id=server_id,
        description=description, image_id=image_id,
    )


@mcp.tool()
def resize_server(
    server_type: str, server_id: int | None = None,
    server_name: str | None = None, upgrade_disk: bool = False,
) -> dict:
    """Đổi loại VPS khi máy đã tắt; có thể nâng dung lượng đĩa."""
    return tools.resize_server(
        get_client(), server_type=server_type, server_id=server_id,
        server_name=server_name, upgrade_disk=upgrade_disk,
    )


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
