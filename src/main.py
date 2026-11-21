from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, cast

from fastapi import Depends, FastAPI, HTTPException, Request
from neo4j import Driver, GraphDatabase
from neo4j.exceptions import AuthError, ServiceUnavailable

from src.config import settings
from src.graph.writer import IngestSummary, ingest_dataset
from src.models.domain import IamDataset


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # The driver connects lazily, so the API starts even if Neo4j is not up yet.
    app.state.driver = GraphDatabase.driver(
        settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
    )
    yield
    app.state.driver.close()


app = FastAPI(title="edte-iam-service", version="0.1.0", lifespan=lifespan)


def get_driver(request: Request) -> Driver:
    return cast(Driver, request.app.state.driver)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/iam/ingest", response_model=IngestSummary)
def ingest(
    dataset: IamDataset, driver: Annotated[Driver, Depends(get_driver)]
) -> IngestSummary:
    """Ingest a batch of users, roles and policies. Safe to call repeatedly."""
    try:
        return ingest_dataset(driver, dataset)
    except (ServiceUnavailable, AuthError) as exc:
        raise HTTPException(status_code=503, detail=f"Neo4j is not available: {exc}") from exc
