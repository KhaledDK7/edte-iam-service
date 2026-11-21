"""Integration test: needs Docker running. Starts a throwaway Neo4j container."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from neo4j import Driver

from src.graph.writer import ingest_dataset
from src.services.parsers import load_dataset

try:
    from testcontainers.community.neo4j import Neo4jContainer
except ImportError:  # older testcontainers releases
    from testcontainers.neo4j import Neo4jContainer  # type: ignore[no-redef]

DATA = Path(__file__).resolve().parents[2] / "data"


@pytest.fixture(scope="module")
def driver() -> Iterator[Driver]:
    try:
        container = Neo4jContainer("neo4j:5")
        container.start()
    except Exception as exc:  # noqa: BLE001 - Docker not running or image cannot be pulled
        pytest.skip(f"Docker/Neo4j container not available: {exc}")
    try:
        neo4j_driver = container.get_driver()
        yield neo4j_driver
        neo4j_driver.close()
    finally:
        container.stop()


def _counts(driver: Driver) -> dict[str, int]:
    with driver.session() as session:
        nodes = session.run("MATCH (n) RETURN count(n) AS c").single()
        rels = session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()
    assert nodes is not None and rels is not None
    return {"nodes": nodes["c"], "relationships": rels["c"]}


def test_reingest_creates_no_duplicates(driver: Driver) -> None:
    dataset = load_dataset(DATA / "users.json", DATA / "roles.json", DATA / "policies.json")

    first = ingest_dataset(driver, dataset)
    after_first = _counts(driver)
    # 6 actors + 10 roles + 6 resource stubs; 7 ASSIGNED_TO + 7 INHERITS_FROM + 8 GRANTS
    assert after_first == {"nodes": 22, "relationships": 22}
    assert first.nodes_created == 22
    assert first.relationships_created == 22

    second = ingest_dataset(driver, dataset)
    assert _counts(driver) == after_first
    assert second.nodes_created == 0
    assert second.relationships_created == 0
