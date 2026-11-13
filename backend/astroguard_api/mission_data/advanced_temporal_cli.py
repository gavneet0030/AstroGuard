from __future__ import annotations

import argparse
import json
import sys

from pathlib import Path

from astroguard_api.mission_data.advanced_temporal import (
    build_advanced_dataset,
    AdvancedFeatureError,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="AstroGuard advanced temporal feature engineering"
    )

    parser.add_argument("--root", required=True)
    parser.add_argument("--channel", required=True)
    parser.add_argument("--spacecraft", default="SMAP")
    parser.add_argument("--overwrite", action="store_true")

    return parser


def main() -> int:
    args = build_parser().parse_args()

    try:
        manifest = build_advanced_dataset(
            project_root=Path(args.root),
            channel_id=args.channel,
            spacecraft=args.spacecraft,
            overwrite=args.overwrite,
        )

        print(json.dumps(manifest, indent=2))
        print("ADVANCED_FEATURE_ENGINEERING_PASS")

        return 0

    except (AdvancedFeatureError, ValueError, OSError) as exc:
        print(
            json.dumps({
                "status": "error",
                "message": str(exc),
            }),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())