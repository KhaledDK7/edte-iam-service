from pathlib import Path

from src.graph.writer import build_rows, ingest_dataset, load_constraints
from src.models.domain import Action, Actor, Grant, IamDataset, Role
from src.services.parsers import load_dataset

DATA = Path(__file__).resolve().parents[2] / "data"


def _sample() -> IamDataset:
    return load_dataset(DATA / "users.json", DATA / "roles.json", DATA / "policies.json")


def test_constraints_are_loaded() -> None:
    statements = load_constraints()
    assert len(statements) == 7
    assert all(s.startswith("CREATE CONSTRAINT") for s in statements)


def test_build_rows_counts_for_sample_data() -> None:
    rows = build_rows(_sample())
    assert len(rows["actors"]) == 6
    assert len(rows["roles"]) == 10
    assert len(rows["assignments"]) == 7
    assert len(rows["inheritances"]) == 7
    assert len(rows["grants"]) == 8


def test_build_rows_content() -> None:
    dataset = IamDataset(
        users=[
            Actor(urn="urn:actor:a", name="A", department="D", roles=["urn:role:r1", "urn:role:r2"])
        ],
        roles=[Role(urn="urn:role:r1", name="R1", inherits_from=["urn:role:r2"])],
        policies=[
            Grant(role="urn:role:r2", resource="urn:resource:s:t:n", action=Action.WRITE)
        ],
    )
    rows = build_rows(dataset)
    assert rows["assignments"] == [
        {"actor": "urn:actor:a", "role": "urn:role:r1"},
        {"actor": "urn:actor:a", "role": "urn:role:r2"},
    ]
    assert rows["inheritances"] == [{"child": "urn:role:r1", "parent": "urn:role:r2"}]
    assert rows["grants"] == [
        {"role": "urn:role:r2", "resource": "urn:resource:s:t:n", "action": "WRITE"}
    ]


def test_every_write_statement_uses_merge(fake_driver) -> None:  # type: ignore[no-untyped-def]
    ingest_dataset(fake_driver, _sample())
    write_queries = [q for q, _ in fake_driver.log if "UNWIND" in q]
    assert len(write_queries) == 5
    for query in write_queries:
        assert "MERGE" in query
        assert "CREATE" not in query


def test_constraints_run_before_writes(fake_driver) -> None:  # type: ignore[no-untyped-def]
    ingest_dataset(fake_driver, _sample())
    queries = [q for q, _ in fake_driver.log]
    first_write = next(i for i, q in enumerate(queries) if "UNWIND" in q)
    assert first_write == 7
    assert all("CREATE CONSTRAINT" in q for q in queries[:first_write])


def test_summary_counts(fake_driver) -> None:  # type: ignore[no-untyped-def]
    summary = ingest_dataset(fake_driver, _sample())
    assert summary.actors_written == 6
    assert summary.roles_written == 10
    assert summary.grants_written == 8
    # The fake reports 1 node and 2 relationships created for each of the 5 steps.
    assert summary.nodes_created == 5
    assert summary.relationships_created == 10
