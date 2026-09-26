import asyncio
from types import SimpleNamespace as Obj
from unittest.mock import Mock, patch

import pytest
from hcloud import APIException
from hcloud.images import Image
from hcloud.locations import Location
from hcloud.server_types import ServerType

from hetzner_vps_tool import tools
from hetzner_vps_tool.client import get_client
from hetzner_vps_tool.mcp_server import mcp


def server(server_id=7, name="vps-a"):
    return Obj(
        id=server_id, name=name, status="running",
        public_net=Obj(ipv4=Obj(ip="192.0.2.10"), ipv6=None),
        server_type=Obj(name="cx23"), datacenter=Obj(name="fsn1-dc14"),
        location=Obj(name="fsn1"), delete=Mock(return_value=Obj(id=91, status="running")),
        create_image=Mock(return_value=Obj(image=Obj(id=23), action=Obj(id=92, status="running"))),
        rebuild=Mock(return_value=Obj(action=Obj(id=93, status="running"), root_password="generated")),
        change_type=Mock(return_value=Obj(id=94, status="running")),
    )


def test_list_servers_formats_fields():
    client = Mock()
    client.servers.get_all.return_value = [server()]
    assert tools.list_servers(client) == [{
        "id": 7, "name": "vps-a", "status": "running", "ipv4": "192.0.2.10",
        "ipv6": None, "server_type": "cx23", "datacenter": "fsn1-dc14",
        "location": "fsn1",
    }]
    client.servers.get_all.assert_called_once_with()


def test_manage_server_create_uses_sdk_models_and_returns_action():
    client = Mock()
    client.servers.create.return_value = Obj(
        server=server(), action=Obj(id=5, status="running"), root_password="generated",
    )
    result = tools.manage_server(
        client, "create", name="vps-a", server_type="cx23",
        image="ubuntu-24.04", location="fsn1",
    )
    kwargs = client.servers.create.call_args.kwargs
    assert kwargs["name"] == "vps-a"
    assert isinstance(kwargs["server_type"], ServerType) and kwargs["server_type"].name == "cx23"
    assert isinstance(kwargs["image"], Image) and kwargs["image"].name == "ubuntu-24.04"
    assert isinstance(kwargs["location"], Location) and kwargs["location"].name == "fsn1"
    assert result["action_id"] == 5 and result["root_password"] == "generated"


def test_manage_server_delete_by_name_and_missing():
    client = Mock()
    target = server()
    client.servers.get_by_name.return_value = target
    assert tools.manage_server(client, "delete", server_name="vps-a")["server_id"] == 7
    client.servers.get_by_name.assert_called_once_with("vps-a")
    target.delete.assert_called_once_with()
    client.servers.get_by_id.return_value = None
    with pytest.raises(ValueError, match="Không tìm thấy server"):
        tools.manage_server(client, "delete", server_id=999)
    client.servers.get_by_id.side_effect = APIException("not_found", "missing", None)
    with pytest.raises(ValueError, match="Không tìm thấy server"):
        tools.manage_server(client, "delete", server_id=999)


def test_manage_snapshot_create():
    client = Mock()
    target = server()
    client.servers.get_by_id.return_value = target
    result = tools.manage_snapshot(client, "create", server_id=7, description="before deploy")
    target.create_image.assert_called_once_with(description="before deploy", type="snapshot")
    assert result["image_id"] == 23 and result["action_id"] == 92


def test_manage_snapshot_restore_and_delete_only_snapshot():
    client = Mock()
    image = Obj(id=23, type="snapshot", delete=Mock(return_value=True))
    client.images.get_by_id.return_value = image
    target = server()
    client.servers.get_by_id.return_value = target
    result = tools.manage_snapshot(client, "restore", server_id=7, image_id=23)
    target.rebuild.assert_called_once_with(image=image)
    assert result["root_password"] == "generated" and result["action_id"] == 93
    assert tools.manage_snapshot(client, "delete", image_id=23)["deleted"] is True
    image.delete.assert_called_once_with()
    image.type = "system"
    with pytest.raises(ValueError, match="không phải snapshot"):
        tools.manage_snapshot(client, "delete", image_id=23)
    client.images.get_by_id.return_value = None
    with pytest.raises(ValueError, match="Không tìm thấy image"):
        tools.manage_snapshot(client, "restore", server_id=7, image_id=999)
    client.images.get_by_id.side_effect = APIException("not_found", "missing", None)
    with pytest.raises(ValueError, match="Không tìm thấy image"):
        tools.manage_snapshot(client, "delete", image_id=999)


def test_resize_server_uses_type_and_upgrade_disk():
    client = Mock()
    target = server()
    client.servers.get_by_id.return_value = target
    result = tools.resize_server(client, server_type="cx33", server_id=7, upgrade_disk=True)
    kwargs = target.change_type.call_args.kwargs
    assert isinstance(kwargs["server_type"], ServerType) and kwargs["server_type"].name == "cx33"
    assert kwargs["upgrade_disk"] is True
    assert result["action_id"] == 94


def test_validation_before_sdk_call():
    client = Mock()
    with pytest.raises(ValueError, match="Thiếu image"):
        tools.manage_server(client, "create", name="x", server_type="cx23", location="fsn1")
    with pytest.raises(ValueError, match="đúng một"):
        tools.resize_server(client, server_type="cx33")
    with pytest.raises(ValueError, match="Thiếu description"):
        tools.manage_snapshot(client, "create", server_id=7)
    client.assert_not_called()


def test_token_only_from_named_environment_variable(monkeypatch):
    monkeypatch.delenv("HCLOUD_API_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="HCLOUD_API_TOKEN"):
        get_client()
    monkeypatch.setenv("HCLOUD_API_TOKEN", "  fake-token  ")
    with patch("hetzner_vps_tool.client.Client") as ctor:
        get_client()
    assert ctor.call_args.kwargs["token"] == "fake-token"


def test_mcp_registers_exactly_four_tools():
    assert {tool.name for tool in asyncio.run(mcp.list_tools())} == {
        "list_servers", "manage_server", "manage_snapshot", "resize_server",
    }
