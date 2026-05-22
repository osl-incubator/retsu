"""Minimal Retsu command line interface."""

from __future__ import annotations

import argparse

from retsu.config import configure
from retsu.task import (
    cleanup_expired_leases,
    define_concurrency,
    define_resource,
    get_usage,
    list_leases,
)


def main(argv: list[str] | None = None) -> int:
    """Run the CLI."""
    parser = argparse.ArgumentParser(prog="retsu")
    parser.add_argument("--backend", default="redis")
    parser.add_argument("--redis-url", default=None)
    parser.add_argument("--namespace", default="default")
    subparsers = parser.add_subparsers(dest="command", required=True)

    resource_parser = subparsers.add_parser("resource")
    resource_parser.add_argument("name")
    resource_parser.add_argument("capacity", type=float)

    concurrency_parser = subparsers.add_parser("concurrency")
    concurrency_parser.add_argument("name")
    concurrency_parser.add_argument("capacity", type=float)

    subparsers.add_parser("usage")
    subparsers.add_parser("leases")
    subparsers.add_parser("cleanup")

    args = parser.parse_args(argv)
    configure(
        backend=args.backend,
        redis_url=args.redis_url,
        namespace=args.namespace,
    )

    if args.command == "resource":
        define_resource(args.name, args.capacity)
        print(f"defined resource {args.name}={args.capacity:g}")
        return 0
    if args.command == "concurrency":
        define_concurrency(args.name, args.capacity)
        print(f"defined concurrency {args.name}={args.capacity:g}")
        return 0
    if args.command == "usage":
        usage = get_usage()
        _print_usage("RESOURCES", usage.resources)
        _print_usage("CONCURRENCY", usage.concurrency)
        return 0
    if args.command == "leases":
        for lease in list_leases():
            print(
                f"{lease.id} job={lease.job_id} owner={lease.owner_id} "
                f"expires_at={lease.expires_at.isoformat()}"
            )
        return 0
    if args.command == "cleanup":
        result = cleanup_expired_leases()
        print(f"expired {len(result.expired_lease_ids)} leases")
        return 0
    return 1


def _print_usage(title: str, items) -> None:
    print(title)
    print("name\tused\tcapacity\tavailable")
    for name, item in items.items():
        print(
            f"{name}\t{item.used:g}\t{item.capacity:g}\t{item.available:g}"
        )


if __name__ == "__main__":
    raise SystemExit(main())

