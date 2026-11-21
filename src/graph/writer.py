"""Idempotent writes of IAM data into Neo4j.

Every statement uses MERGE on the canonical URN, so ingesting the same data twice
creates no duplicate nodes or relationships.
"""

from pathlib import Path
from typing import LiteralString

from neo4j import Driver, ManagedTransaction
from pydantic import BaseModel

from src.models.domain import IamDataset

CONSTRAINTS_FILE = Path(__file__).resolve().parents[2] / "schema" / "constraints.cypher"

_ACTORS: LiteralString = """
UNWIND $rows AS row
MERGE (a:Actor {urn: row.urn})
SET a.name = row.name, a.department = row.department
"""

_ROLES: LiteralString = """
UNWIND $rows AS row
MERGE (r:Role {urn: row.urn})
SET r.name = row.name
"""

_ASSIGNMENTS: LiteralString = """
UNWIND $rows AS row
MERGE (a:Actor {urn: row.actor})
MERGE (r:Role {urn: row.role})
MERGE (a)-[:ASSIGNED_TO]->(r)
"""

_INHERITANCES: LiteralString = """
UNWIND $rows AS row
MERGE (child:Role {urn: row.child})
MERGE (parent:Role {urn: row.parent})
MERGE (child)-[:INHERITS_FROM]->(parent)
"""

# Resource nodes are owned by Team 1, so only a stub keyed by urn is merged here.
_GRANTS: LiteralString = """
UNWIND $rows AS row
MERGE (r:Role {urn: row.role})
MERGE (res:Resource {urn: row.resource})
MERGE (r)-[:GRANTS {action: row.action}]->(res)
"""

# Order matters: nodes first, then the relationships between them.
_STEPS: list[tuple[LiteralString, str]] = [
    (_ACTORS, "actors"),
    (_ROLES, "roles"),
    (_ASSIGNMENTS, "assignments"),
    (_INHERITANCES, "inheritances"),
    (_GRANTS, "grants"),
]

Rows = dict[str, list[dict[str, str]]]


class IngestSummary(BaseModel):
    actors_written: int
    roles_written: int
    grants_written: int
    nodes_created: int
    relationships_created: int


def load_constraints(path: Path = CONSTRAINTS_FILE) -> list[str]:
    """Read the global constraint statements, one per ';'-terminated statement."""
    text = path.read_text(encoding="utf-8")
    lines = [line for line in text.splitlines() if not line.strip().startswith("//")]
    return [s.strip() for s in "\n".join(lines).split(";") if s.strip()]


def build_rows(dataset: IamDataset) -> Rows:
    return {
        "actors": [
            {"urn": a.urn, "name": a.name, "department": a.department} for a in dataset.users
        ],
        "roles": [{"urn": r.urn, "name": r.name} for r in dataset.roles],
        "assignments": [
            {"actor": a.urn, "role": role} for a in dataset.users for role in a.roles
        ],
        "inheritances": [
            {"child": r.urn, "parent": parent} for r in dataset.roles for parent in r.inherits_from
        ],
        "grants": [
            {"role": g.role, "resource": g.resource, "action": g.action.value}
            for g in dataset.policies
        ],
    }


def _write_all(tx: ManagedTransaction, rows: Rows) -> tuple[int, int]:
    nodes = relationships = 0
    for query, key in _STEPS:
        counters = tx.run(query, rows=rows[key]).consume().counters
        nodes += counters.nodes_created
        relationships += counters.relationships_created
    return nodes, relationships


def ingest_dataset(driver: Driver, dataset: IamDataset) -> IngestSummary:
    """Create the constraints, then write the whole dataset in one transaction."""
    rows = build_rows(dataset)
    with driver.session() as session:
        for statement in load_constraints():
            session.run(statement).consume()
        nodes, relationships = session.execute_write(_write_all, rows)
    return IngestSummary(
        actors_written=len(rows["actors"]),
        roles_written=len(rows["roles"]),
        grants_written=len(rows["grants"]),
        nodes_created=nodes,
        relationships_created=relationships,
    )
