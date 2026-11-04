"""Minimal training/evaluation CLI."""
import argparse
import json

from .model import run


def main():
    parser = argparse.ArgumentParser(prog="roguecast")
    parser.add_argument("command", choices=["train", "evaluate"])
    parser.add_argument("--input", required=True, help="Approved, labeled agent-session snapshots (CSV)")
    parser.add_argument("--output", required=True, help="Private model path for train; report JSON for evaluate")
    parser.add_argument("--horizon-minutes", type=int, default=30)
    args = parser.parse_args()
    if args.horizon_minutes <= 0:
        parser.error("--horizon-minutes must be positive")
    report = run(args.input, args.output if args.command == "train" else None,
                 args.horizon_minutes)
    if args.command == "evaluate":
        with open(args.output, "w", encoding="utf-8") as file:
            json.dump(report, file, indent=2)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
