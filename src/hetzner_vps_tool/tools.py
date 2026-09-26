"""Exactly four public operations. All SDK access goes through the injected client."""

from typing import Any

from hcloud import APIException
from hcloud.images import Image
from hcloud.locations import Location
from hcloud.server_types import ServerType


def _required(value: Any, label: str) -> Any:
    if value is None or isinstance(value, str) and not value.strip():
        raise ValueError(f"Thiếu {label}")
    return value


def _server(client: Any, server_id: int | None, server_name: str | None) -> Any:
    if (server_id is None) == (server_name is None):
        raise ValueError("Cần đúng một trong server_id hoặc server_name")
    try:
        server = (client.servers.get_by_id(server_id) if server_id is not None
                  else client.servers.get_by_name(_required(server_name, "server_name")))
    except APIException as exc:
        if exc.code in (404, "not_found"):
            raise ValueError("Không tìm thấy server") from exc
        raise
    if server is None:
        raise ValueError("Không tìm thấy server")
    return server


def _action(action: Any) -> dict[str, Any]:
    return {"action_id": getattr(action, "id", None),
            "action_status": getattr(action, "status", None)}


def _server_info(server: Any) -> dict[str, Any]:
    public_net = getattr(server, "public_net", None)
    ipv4 = getattr(public_net, "ipv4", None)
    ipv6 = getattr(public_net, "ipv6", None)
    datacenter = getattr(server, "datacenter", None)
    location = getattr(server, "location", None)
    return {
        "id": server.id,
        "name": server.name,
        "status": server.status,
        "ipv4": getattr(ipv4, "ip", None),
        "ipv6": getattr(ipv6, "ip", None),
        "server_type": getattr(getattr(server, "server_type", None), "name", None),
        "datacenter": getattr(datacenter, "name", None),
        "location": getattr(location, "name", None),
    }


def list_servers(client: Any) -> list[dict[str, Any]]:
    """Liệt kê mọi server và thông tin mạng, loại máy, datacenter."""
    return [_server_info(server) for server in client.servers.get_all()]


def manage_server(
    client: Any, action: str, *, name: str | None = None,
    server_type: str | None = None, image: str | int | None = None,
    location: str | None = None, server_id: int | None = None,
    server_name: str | None = None,
) -> dict[str, Any]:
    """Tạo server ở location hoặc xóa server theo ID/tên."""
    if action == "create":
        _required(name, "name")
        _required(server_type, "server_type")
        _required(image, "image")
        _required(location, "location")
        image_ref = Image(id=image) if isinstance(image, int) else Image(name=image)
        response = client.servers.create(
            name=name, server_type=ServerType(name=server_type),
            image=image_ref, location=Location(name=location),
        )
        result = {"operation": "create", "server": _server_info(response.server),
                  **_action(response.action)}
        if response.root_password is not None:
            result["root_password"] = response.root_password
        return result
    if action == "delete":
        server = _server(client, server_id, server_name)
        result = {"operation": "delete", "server_id": server.id,
                  **_action(server.delete())}
        return result
    raise ValueError("action phải là create hoặc delete")


def manage_snapshot(
    client: Any, action: str, *, server_id: int | None = None,
    description: str | None = None, image_id: int | None = None,
) -> dict[str, Any]:
    """Tạo snapshot, rebuild server từ snapshot, hoặc xóa snapshot."""
    if action == "create":
        _required(server_id, "server_id")
        _required(description, "description")
        server = _server(client, server_id, None)
        response = server.create_image(description=description, type="snapshot")
        return {"operation": "create", "server_id": server.id,
                "image_id": response.image.id, **_action(response.action)}
    if action in ("restore", "delete"):
        _required(image_id, "image_id")
        try:
            image = client.images.get_by_id(image_id)
        except APIException as exc:
            if exc.code in (404, "not_found"):
                raise ValueError("Không tìm thấy image") from exc
            raise
        if image is None:
            raise ValueError("Không tìm thấy image")
        if image.type != "snapshot":
            raise ValueError("Image không phải snapshot")
        if action == "delete":
            return {"operation": "delete", "image_id": image.id,
                    "deleted": image.delete()}
        _required(server_id, "server_id")
        server = _server(client, server_id, None)
        response = server.rebuild(image=image)
        result = {"operation": "restore", "server_id": server.id,
                  "image_id": image.id, **_action(response.action)}
        if response.root_password is not None:
            result["root_password"] = response.root_password
        return result
    raise ValueError("action phải là create, restore hoặc delete")


def resize_server(
    client: Any, *, server_type: str, server_id: int | None = None,
    server_name: str | None = None, upgrade_disk: bool = False,
) -> dict[str, Any]:
    """Đổi server type; Hetzner yêu cầu server đã tắt."""
    _required(server_type, "server_type")
    server = _server(client, server_id, server_name)
    action = server.change_type(
        server_type=ServerType(name=server_type), upgrade_disk=upgrade_disk,
    )
    return {"server_id": server.id, "server_type": server_type,
            "upgrade_disk": upgrade_disk, **_action(action)}
