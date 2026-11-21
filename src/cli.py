"""Command line interface: python -m src.cli <command>."""

import argparse
import sys
from pathlib import Path

from neo4j import Driver, GraphDatabase
from neo4j.exceptions import AuthError, ServiceUnavailable

from src.config import settings
from src.graph.writer import ingest_dataset
from src.services.parsers import ParseError, load_dataset


def _connect() -> Driver:
    return GraphDatabase.driver(
        settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
    )


def _ingest(args: argparse.Namespace) -> int:
    try:
        dataset = load_dataset(Path(args.users), Path(args.roles), Path(args.policies))
    except ParseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    driver = _connect()
    try:
        summary = ingest_dataset(driver, dataset)
    except (ServiceUnavailable, AuthError) as exc:
        print(f"error: Neo4j is not available: {exc}", file=sys.stderr)
        return 1
    finally:
        driver.close()

    print(
        f"Ingested {summary.actors_written} actors, {summary.roles_written} roles, "
        f"{summary.grants_written} grants "
        f"({summary.nodes_created} nodes and {summary.relationships_created} "
        f"relationships newly created)."
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="edte-iam")
    commands = parser.add_subparsers(dest="command", required=True)

    ingest = commands.add_parser("ingest-iam", help="Load users, roles and policies into Neo4j")
    ingest.add_argument("--users", required=True, help="users .json or .csv file")
    ingest.add_argument("--roles", required=True, help="roles .json or .csv file")
    ingest.add_argument("--policies", required=True, help="policies .json or .csv file")
    ingest.set_defaults(handler=_ingest)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    sys.exit(main())
