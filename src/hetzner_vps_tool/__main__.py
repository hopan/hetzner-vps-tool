"""Small JSON CLI for the four operations."""

import argparse
import json
import sys

from hcloud import HCloudException

from .client import get_client
from . import tools


def main() -> None:
    parser = argparse.ArgumentParser(prog="hetzner-vps")
    commands = parser.add_subparsers(dest="tool", required=True)
    commands.add_parser("list_servers")

    server = commands.add_parser("manage_server")
    server.add_argument("action", choices=("create", "delete"))
    server.add_argument("--name")
    server.add_argument("--server-type")
    server.add_argument("--image")
    server.add_argument("--location")
    server.add_argument("--server-id", type=int)
    server.add_argument("--server-name")

    snapshot = commands.add_parser("manage_snapshot")
    snapshot.add_argument("action", choices=("create", "restore", "delete"))
    snapshot.add_argument("--server-id", type=int)
    snapshot.add_argument("--description")
    snapshot.add_argument("--image-id", type=int)

    resize = commands.add_parser("resize_server")
    resize.add_argument("--server-type", required=True)
    resize.add_argument("--server-id", type=int)
    resize.add_argument("--server-name")
    resize.add_argument("--upgrade-disk", action="store_true")

    args = parser.parse_args()
    try:
        client = get_client()
        if args.tool == "list_servers":
            result = tools.list_servers(client)
        elif args.tool == "manage_server":
            result = tools.manage_server(
                client, args.action, name=args.name,
                server_type=args.server_type,
                image=int(args.image) if args.image and args.image.isdecimal() else args.image,
                location=args.location, server_id=args.server_id,
                server_name=args.server_name,
            )
        elif args.tool == "manage_snapshot":
            result = tools.manage_snapshot(
                client, args.action, server_id=args.server_id,
                description=args.description, image_id=args.image_id,
            )
        else:
            result = tools.resize_server(
                client, server_type=args.server_type,
                server_id=args.server_id, server_name=args.server_name,
                upgrade_disk=args.upgrade_disk,
            )
    except (ValueError, RuntimeError, HCloudException) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
