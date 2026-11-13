import argparse
import json
from pathlib import Path

from .config import ExperimentConfig
from .experiments import run_experiments


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--root", required=True)
    parser.add_argument("--output", required=True)

    parser.add_argument(
        "--feature-set",
        default="advanced",
        choices=["advanced", "baseline"]
    )

    args = parser.parse_args()

    config = ExperimentConfig(
        feature_set=args.feature_set
    )

    result = run_experiments(
        Path(args.root),
        Path(args.output),
        config
    )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()