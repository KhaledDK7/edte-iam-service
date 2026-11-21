from pathlib import Path

import pytest

from src import cli

DATA = Path(__file__).resolve().parents[2] / "data"


def _args() -> list[str]:
    return [
        "ingest-iam",
        "--users", str(DATA / "users.json"),
        "--roles", str(DATA / "roles.json"),
        "--policies", str(DATA / "policies.json"),
    ]


def test_ingest_success(monkeypatch, capsys, fake_driver) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(cli, "_connect", lambda: fake_driver)
    assert cli.main(_args()) == 0
    assert "Ingested 6 actors, 10 roles, 8 grants" in capsys.readouterr().out
    assert fake_driver.closed


def test_ingest_invalid_file(monkeypatch, capsys, fake_driver, tmp_path) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(cli, "_connect", lambda: fake_driver)
    bad = tmp_path / "users.json"
    bad.write_text('[{"urn": "bad", "name": "A", "department": "X"}]', encoding="utf-8")
    args = _args()
    args[2] = str(bad)
    assert cli.main(args) == 1
    assert "record 1" in capsys.readouterr().err
    assert fake_driver.log == []


def test_missing_arguments_exit() -> None:
    with pytest.raises(SystemExit) as exc:
        cli.main(["ingest-iam", "--users", "u.json"])
    assert exc.value.code == 2
