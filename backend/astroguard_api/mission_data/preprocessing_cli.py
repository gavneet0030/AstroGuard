from __future__ import annotations

import argparse
import json
from pathlib import Path

from .preprocessing import (
    DEFAULT_WINDOWS,
    PreprocessingError,
    preprocess_channel,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="AstroGuard telemetry preprocessing CLI"
    )

    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="AstroGuard project root",
    )

    parser.add_argument(
        "--channel",
        required=True,
        help="Channel ID, for example A-1 or P-1",
    )

    parser.add_argument(
        "--spacecraft",
        default="SMAP",
        help="Spacecraft identifier (default: SMAP)",
    )

    parser.add_argument(
        "--windows",
        nargs="+",
        type=int,
        default=list(DEFAULT_WINDOWS),
        help="Rolling windows, for example: --windows 5 30",
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing processed outputs",
    )

    return parser


def main() -> int:
    args = build_parser().parse_args()

    try:
        result = preprocess_channel(
            project_root=args.root,
            channel_id=args.channel,
            spacecraft=args.spacecraft,
            windows=args.windows,
            overwrite=args.overwrite,
        )

    except PreprocessingError as exc:
        print(
            json.dumps(
                {"status": "error", "message": str(exc)},
                indent=2,
            )
        )
        return 2

    print(
        json.dumps(
            {
                "status": "success",
                "channel_id": result["channel_id"],
                "spacecraft": result["spacecraft"],
                "train_shape": result["train_shape"],
                "test_shape": result["test_shape"],
                "labels_shape": result["labels_shape"],
                "engineered_feature_count": result["engineered_feature_count"],
                "anomaly_row_count": result["anomaly_row_count"],
                "manifest_path": result["manifest_path"],
                "output_directory": result["output_directory"],
            },
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
