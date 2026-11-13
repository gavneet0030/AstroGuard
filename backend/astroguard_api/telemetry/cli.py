"""
AstroGuard telemetry ingestion command-line interface.

Example:
python -m astroguard_api.telemetry.cli ingest data/sample/file.csv
"""

from __future__ import annotations

import argparse
import json
import sys

from pathlib import Path

from astroguard_api.telemetry.ingestion import (
    IngestionError,
    TelemetryIngestor,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="astroguard-telemetry",
        description=(
            "Ingest historical telemetry CSV or JSON files."
        ),
    )

    parser.add_argument(
        "--project-root",
        default=None,
        help="AstroGuard project root.",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    ingest = subparsers.add_parser(
        "ingest",
        help="Ingest a telemetry file.",
    )

    ingest.add_argument(
        "source",
        help="Path to a CSV or JSON telemetry file.",
    )

    ingest.add_argument(
        "--source-label",
        default="LOCAL_FILE",
        help="Provenance label for the source.",
    )

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)

    root = (
        Path(arguments.project_root).resolve()
        if arguments.project_root
        else Path(__file__).resolve().parents[3]
    )

    try:
        ingestor = TelemetryIngestor(root)

        result = ingestor.ingest_file(
            Path(arguments.source),
            source_label=arguments.source_label,
        )

        print(
            json.dumps(
                result.to_dict(),
                indent=2,
                sort_keys=True,
            )
        )

        return 0

    except IngestionError as exc:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "error": str(exc),
                },
                indent=2,
            ),
            file=sys.stderr,
        )

        return 2

    except OSError:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "error": "File system operation failed.",
                },
                indent=2,
            ),
            file=sys.stderr,
        )

        return 3


if __name__ == "__main__":
    raise SystemExit(main())
