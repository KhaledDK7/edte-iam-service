import pytest
from pydantic import ValidationError

from src.models.domain import Action, Actor, Grant, Role


def test_valid_actor() -> None:
    actor = Actor(
        urn="urn:actor:intern_khaled",
        name="Khaled",
        department="Finance",
        roles=["urn:role:intern"],
    )
    assert actor.roles == ["urn:role:intern"]


@pytest.mark.parametrize("urn", ["intern_khaled", "urn:role:intern", "urn:actor:", "urn:actor:a b"])
def test_invalid_actor_urn(urn: str) -> None:
    with pytest.raises(ValidationError):
        Actor(urn=urn, name="X", department="Y")


def test_role_can_inherit() -> None:
    role = Role(urn="urn:role:intern", name="Intern", inherits_from=["urn:role:finance_operator"])
    assert role.inherits_from == ["urn:role:finance_operator"]


def test_role_rejects_actor_urn_as_parent() -> None:
    with pytest.raises(ValidationError):
        Role(urn="urn:role:intern", name="Intern", inherits_from=["urn:actor:bob"])


def test_valid_grant() -> None:
    grant = Grant(
        role="urn:role:finance_operator",
        resource="urn:resource:billing_db:table:invoices",
        action="WRITE",
    )
    assert grant.action is Action.WRITE


@pytest.mark.parametrize(
    "resource",
    ["billing_db.invoices", "urn:resource:billing_db:invoices", "urn:actor:x:y:z"],
)
def test_invalid_resource_urn(resource: str) -> None:
    with pytest.raises(ValidationError):
        Grant(role="urn:role:r", resource=resource, action="READ")


def test_invalid_action() -> None:
    with pytest.raises(ValidationError):
        Grant(
            role="urn:role:r",
            resource="urn:resource:db:table:t",
            action="DELETE",
        )


def test_extra_fields_rejected() -> None:
    with pytest.raises(ValidationError):
        Role.model_validate({"urn": "urn:role:r", "name": "R", "colour": "red"})
