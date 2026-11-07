"""Run the retained GS120 Section 5.2 control with the new neighborhood producer."""

import argparse
import sys
from pathlib import Path

from corpus_structure.methods.contextual_candidates import ContextualCandidatesWithNeighborhood
from corpus_structure.settings import Settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--release", required=True)
    args = parser.parse_args()
    evidence = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(evidence / "2026-11-07_nce06-closeout"))
    import replay_headings

    settings = Settings()
    replay_headings.ContextualCandidates = ContextualCandidatesWithNeighborhood
    args.output.mkdir(parents=True, exist_ok=False)
    prepared = replay_headings.prepared_release(settings, args.output, args.release)
    replay_headings.run_case(
        settings, prepared, args.output, "5.2", replay_headings.frozen_sources()
    )


if __name__ == "__main__":
    main()
