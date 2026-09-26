"""Create the SDK client only when a CLI or MCP tool is invoked."""

import os

from hcloud import Client


def get_client() -> Client:
    token = os.environ.get("HCLOUD_API_TOKEN", "").strip()
    if not token:
        raise RuntimeError("HCLOUD_API_TOKEN chưa được thiết lập")
    return Client(token=token, application_name="hetzner-vps-tool", application_version="0.1.0")
