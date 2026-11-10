"""Explicitly create or replace fictional demo state in the local emulator."""

import argparse

from google.api_core.exceptions import AlreadyExists

from campus_asset_concierge.domain.scenarios import TestScenario
from campus_asset_concierge.storage.local_state import LocalStateStore
from campus_asset_concierge.storage.collection_state import CollectionStateStore


def advance_minutes(value: str) -> int:
    try:
        minutes = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("Use a whole number of minutes.") from error
    if not 0 <= minutes <= 1440:
        raise argparse.ArgumentTypeError("Advance minutes must be between 0 and 1440.")
    return minutes


def main(argv: list[str] | None = None, *, store: LocalStateStore | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", choices=[scenario.value for scenario in TestScenario])
    parser.add_argument("--replace", action="store_true", help="Overwrite existing demo activity.")
    parser.add_argument("--advance-minutes", type=advance_minutes, default=0)
    parser.add_argument("--layout", choices=["legacy", "collections"], default="legacy",
                        help="Use collections only in the Firestore emulator; legacy is unchanged.")
    args = parser.parse_args(argv)
    try:
        store = store if store is not None else (
            CollectionStateStore() if args.layout == "collections" else LocalStateStore()
        )
    except RuntimeError as error:
        parser.exit(1, f"{error}\n")
    print(f"Target: {store.client.project}/(default)/{store.document.path}; scenario: {args.scenario}; "
          f"test clock advance: {args.advance_minutes} minutes; replace: {args.replace}", flush=True)
    try:
        store.seed(TestScenario(args.scenario), replace=args.replace, advance_minutes=args.advance_minutes)
    except AlreadyExists:
        parser.exit(1, "Demo document already exists. Use --replace to overwrite its activity.\n")
    print("Fictional demo state seeded. Recovery has not run.")


if __name__ == "__main__":
    main()
