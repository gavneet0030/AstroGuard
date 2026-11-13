from __future__ import annotations

import argparse
import json
import sys

from pathlib import Path

from astroguard_api.mission_sources.smap_msl import (
    SmapMslSource,
    SourceConnectorError,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="astroguard-mission-source",
        description=(
            "AstroGuard public mission research data source connector."
        ),
    )

    parser.add_argument(
        "--project-root",
        default=str(Path.cwd()),
        help="AstroGuard project root.",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    subparsers.add_parser(
        "discover",
        help="Display registered SMAP/MSL source metadata.",
    )

    fetch = subparsers.add_parser(
        "fetch-labels",
        help="Download and validate the anomaly label CSV.",
    )

    fetch.add_argument(
        "--force",
        action="store_true",
        help="Replace the existing downloaded labels.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    source = SmapMslSource(args.project_root)

    try:
        if args.command == "discover":
            result = source.discover()

        elif args.command == "fetch-labels":
            result = source.run(
                force_download=args.force
            )

        else:
            parser.error("Unsupported command.")
            return 2

        print(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False,
            )
        )

        return 0

    except SourceConnectorError as exc:
        print(
            json.dumps({
                "status": "failed",
                "error_type": type(exc).__name__,
                "message": str(exc),
            }),
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
