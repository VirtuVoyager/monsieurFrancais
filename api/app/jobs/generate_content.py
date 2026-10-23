import argparse
from pathlib import Path

from app.db import SessionLocal
from app.services import generation
from app.services.users import get_or_create_learner


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate or promote catalogue exam items")
    parser.add_argument("action", choices=["generate", "promote"])
    parser.add_argument("request", type=Path, help="a request file in content/generation/")
    args = parser.parse_args()
    if args.action == "promote":
        print(f"Promoted {generation.promote(args.request)} items to the item bank")
        return
    with SessionLocal() as session:
        report = generation.generate(session, get_or_create_learner(session).id, args.request)
    print(
        f"Wrote {len(report.written)} drafts ({report.cached} batches already done): "
        + ", ".join(f"{n} {status}" for status, n in report.counts.items())
    )


if __name__ == "__main__":
    main()
