import json
from pathlib import Path

import pytest

from src.services.parsers import ParseError, load_dataset, parse_roles, parse_users

DATA = Path(__file__).resolve().parents[2] / "data"


def test_sample_dataset_loads() -> None:
    dataset = load_dataset(DATA / "users.json", DATA / "roles.json", DATA / "policies.json")
    assert len(dataset.users) == 6
    assert len(dataset.roles) == 10
    assert len(dataset.policies) == 8


def test_sample_contains_deep_hierarchy() -> None:
    parents = {r.urn: r.inherits_from for r in parse_roles(DATA / "roles.json")}
    depth, role = 0, "urn:role:intern"
    while parents[role] and depth < 20:
        role = parents[role][0]
        depth += 1
    assert depth >= 5


def test_csv_users(tmp_path: Path) -> None:
    file = tmp_path / "users.csv"
    file.write_text(
        "urn,name,department,roles\n"
        "urn:actor:a1,Ann,Finance,urn:role:r1;urn:role:r2\n",
        encoding="utf-8",
    )
    users = parse_users(file)
    assert users[0].roles == ["urn:role:r1", "urn:role:r2"]


def test_invalid_records_are_all_reported(tmp_path: Path) -> None:
    file = tmp_path / "users.json"
    file.write_text(
        json.dumps(
            [
                {"urn": "bad", "name": "A", "department": "X"},
                {"urn": "urn:actor:ok", "name": "B", "department": "X"},
                {"urn": "urn:actor:c", "name": "", "department": "X"},
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(ParseError) as exc:
        parse_users(file)
    message = str(exc.value)
    assert "record 1" in message and "record 3" in message
    assert "record 2" not in message


def test_json_must_be_a_list(tmp_path: Path) -> None:
    file = tmp_path / "roles.json"
    file.write_text("{}", encoding="utf-8")
    with pytest.raises(ParseError):
        parse_roles(file)


def test_malformed_json(tmp_path: Path) -> None:
    file = tmp_path / "roles.json"
    file.write_text("[not json", encoding="utf-8")
    with pytest.raises(ParseError):
        parse_roles(file)


def test_unsupported_extension(tmp_path: Path) -> None:
    file = tmp_path / "roles.xml"
    file.write_text("<x/>", encoding="utf-8")
    with pytest.raises(ParseError):
        parse_roles(file)


def test_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ParseError):
        parse_roles(tmp_path / "nope.json")
