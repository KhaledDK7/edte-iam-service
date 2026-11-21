from types import SimpleNamespace
from typing import Any, Self

import pytest


class FakeResult:
    def consume(self) -> Any:
        return SimpleNamespace(counters=SimpleNamespace(nodes_created=1, relationships_created=2))


class FakeTx:
    def __init__(self, log: list[tuple[str, dict[str, Any]]]) -> None:
        self.log = log

    def run(self, query: str, **params: Any) -> FakeResult:
        self.log.append((query, params))
        return FakeResult()


class FakeSession:
    def __init__(self, log: list[tuple[str, dict[str, Any]]]) -> None:
        self.log = log

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def run(self, query: str, **params: Any) -> FakeResult:
        self.log.append((query, params))
        return FakeResult()

    def execute_write(self, fn: Any, *args: Any) -> Any:
        return fn(FakeTx(self.log), *args)


class FakeDriver:
    """Records every query instead of talking to Neo4j."""

    def __init__(self) -> None:
        self.log: list[tuple[str, dict[str, Any]]] = []
        self.closed = False

    def session(self) -> FakeSession:
        return FakeSession(self.log)

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def fake_driver() -> FakeDriver:
    return FakeDriver()
