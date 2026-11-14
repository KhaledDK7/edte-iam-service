"""Parsers that read and validate IAM input files (JSON or CSV)."""

import csv
import json
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from src.models.domain import Actor, Grant, IamDataset, Role

T = TypeVar("T", bound=BaseModel)

# CSV columns that hold several values separated by semicolons.
_LIST_COLUMNS = {"roles", "inherits_from"}


class ParseError(ValueError):
    """Raised when an input file cannot be read or contains invalid records."""


def _read_records(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    try:
        if suffix == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                raise ParseError(f"{path.name}: expected a JSON list of records")
            return [dict(item) if isinstance(item, dict) else {"_invalid": item} for item in data]
        if suffix == ".csv":
            with path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            return [
                {
                    key: ([v for v in value.split(";") if v] if key in _LIST_COLUMNS else value)
                    for key, value in row.items()
                }
                for row in rows
            ]
    except (OSError, json.JSONDecodeError) as exc:
        raise ParseError(f"{path.name}: {exc}") from exc
    raise ParseError(f"{path.name}: unsupported file type '{suffix}' (use .json or .csv)")


def _validate(model: type[T], records: list[dict[str, Any]], source: str) -> list[T]:
    valid: list[T] = []
    problems: list[str] = []
    for index, record in enumerate(records, start=1):
        try:
            valid.append(model.model_validate(record))
        except ValidationError as exc:
            for error in exc.errors():
                location = ".".join(str(part) for part in error["loc"]) or "record"
                problems.append(f"{source} record {index}: {location}: {error['msg']}")
    if problems:
        raise ParseError("\n".join(problems))
    return valid


def parse_users(path: Path) -> list[Actor]:
    return _validate(Actor, _read_records(path), path.name)


def parse_roles(path: Path) -> list[Role]:
    return _validate(Role, _read_records(path), path.name)


def parse_policies(path: Path) -> list[Grant]:
    return _validate(Grant, _read_records(path), path.name)


def load_dataset(users: Path, roles: Path, policies: Path) -> IamDataset:
    return IamDataset(
        users=parse_users(users),
        roles=parse_roles(roles),
        policies=parse_policies(policies),
    )
