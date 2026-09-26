# Hetzner VPS Tool

Project Python cung cấp đúng 4 tool quản lý server và snapshot Hetzner Cloud bằng SDK chính thức `hcloud`. Client chỉ được tạo khi gọi tool; token lấy duy nhất từ biến môi trường `HCLOUD_API_TOKEN`.

## Bốn tool

| Tool | Tham số | Kết quả |
| --- | --- | --- |
| `list_servers` | không có | Danh sách ID, tên, trạng thái, IPv4/IPv6, server type, datacenter, location |
| `manage_server` | `action=create`: `name`, `server_type`, `image`, `location`; `action=delete`: đúng một trong `server_id`, `server_name` | Thông tin server và action; create có thể trả `root_password` |
| `manage_snapshot` | `action=create`: `server_id`, `description`; `action=restore`: `server_id`, `image_id`; `action=delete`: `image_id` | Image ID, action; restore có thể trả `root_password` |
| `resize_server` | `server_type`, đúng một trong `server_id`, `server_name`, tùy chọn `upgrade_disk` (mặc định `false`) | ID và trạng thái action |

`image` khi tạo server là tên image (ví dụ `ubuntu-22.04`) hoặc ID số. SDK hiện dùng `location=Location(name=...)` khi tạo server; không có tham số datacenter. Trường `datacenter` khi liệt kê là `null` nếu SDK/API không cung cấp thuộc tính đó (hcloud 2.25.1 hiện không khai báo datacenter trong model `Server`); `location` vẫn được trả riêng.

Các thao tác tạo server, tạo snapshot, restore và resize trả action có thể vẫn ở trạng thái `running`; tool không chờ hoàn tất. Restore dùng `server.rebuild(image=...)` và **ghi đè dữ liệu trên ổ đĩa server**. Resize yêu cầu server đã tắt theo quy định Hetzner; tool không tự tắt máy. `upgrade_disk=true` nâng dung lượng đĩa và có thể hạn chế việc đổi xuống loại nhỏ hơn sau này. Snapshot tạo từ server đang chạy có thể chứa dữ liệu đĩa chưa nhất quán; người vận hành cần chuẩn bị ứng dụng trước khi chụp.

## Cài đặt và chạy

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[test]'
export HCLOUD_API_TOKEN='<token do Jack cung cấp khi vận hành>'
.venv/bin/hetzner-vps list_servers
.venv/bin/hetzner-vps manage_server create --name vps-a --server-type ccx13 --image ubuntu-22.04 --location fsn1
.venv/bin/hetzner-vps manage_snapshot create --server-id 123 --description 'before deploy'
.venv/bin/hetzner-vps resize_server --server-id 123 --server-type ccx23
```

Các loại server khả dụng tùy tài khoản; kiểm tra bằng `client.server_types.get_all()` trước khi dùng. Với tài khoản đã test, dòng `ccx*` hoạt động, còn `cpx*` và `cax*` không tạo được. Ví dụ `resize_server` chỉ dùng sau khi server đã tắt.

CLI in JSON ra stdout. `root_password` khi Hetzner cấp sẽ xuất hiện trong JSON của create/restore; Jack cần giữ output này như bí mật. Có thể chạy MCP stdio bằng `.venv/bin/hetzner-vps-mcp`.

Ví dụ cấu hình `.mcp.json` cho Jack (điền token qua cơ chế secret của môi trường vận hành; không commit token):

```json
{
  "mcpServers": {
    "hetzner-vps": {
      "command": "/home/kindling/hetzner-vps-tool/.venv/bin/hetzner-vps-mcp",
      "env": {
        "HCLOUD_API_TOKEN": "<Jack injects token here>"
      }
    }
  }
}
```

## Test và bàn giao

```bash
.venv/bin/python -m pytest -q
```

Mọi test trong bộ `pytest` dùng mock client.

## Đã test với token thật

- `list_servers` hoạt động đúng và trả về `[]` khi project trống.
- `manage_server create` với `server_type=cpx11` và `server_type=cax11` đều bị API từ chối ở `fsn1` và `nbg1` với lỗi `invalid_input: unsupported location for server type`. Tài khoản đã test không tạo được server thuộc hai dòng shared-vCPU AMD (`cpx*`) và ARM (`cax*`).
- `manage_server create` với `server_type=ccx13` tại `fsn1` tạo thành công server ID `167520889`; server này đã được xoá sau khi test.
- Danh sách image thật của tài khoản lúc kiểm tra có `ubuntu-22.04`, không có `ubuntu-24.04`.
- `manage_snapshot` chạy đúng cả ba action `create`, `restore` và `delete` trên server `ccx13` thật: tạo snapshot từ server đang chạy, restore/rebuild thành công và trả `root_password` mới, rồi xoá snapshot thành công.
- `resize_server` khi server đang `running` bị API từ chối với lỗi `server_not_stopped: server must be offline for change of server_type`. Sau khi `power_off` (ngoài phạm vi bốn tool), resize từ `ccx13` sang `ccx23` thành công và server tự khởi động lại.

Mọi server và snapshot dùng để test đã được xoá sạch ngay sau khi hoàn tất; project hiện trống (`list_servers` trả `[]`) và không còn phát sinh phí từ các tài nguyên test.

Chữ ký SDK được đối chiếu với [README chính thức](https://github.com/hetznercloud/hcloud-python), [tài liệu ServersClient](https://hcloud-python.readthedocs.io/en/stable/api.clients.servers.html) và [tài liệu ImagesClient](https://hcloud-python.readthedocs.io/en/stable/api.clients.images.html), sau đó kiểm tra bằng `inspect.signature` trên hcloud 2.25.1 đã cài trong `.venv`.
