"""Run the full FrenchScouts pipeline: fetch -> clean -> analyze.

Usage:
    python main.py            # run all stages (resumable)
    python main.py --force    # re-fetch and re-clean everything
"""
import sys

from fetch import fetch_all
from clean import clean_all
from analyze import analyze_all


def main() -> None:
    force = "--force" in sys.argv
    print("=== 1/3 FETCH ===")
    fetch_all(force=force)
    print("\n=== 2/3 CLEAN ===")
    clean_all(force=force)
    print("\n=== 3/3 ANALYZE ===")
    analyze_all()


if __name__ == "__main__":
    main()
