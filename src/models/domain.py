"""Pydantic v2 domain models for the IAM service."""

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

_ID = r"[A-Za-z0-9_.\-]+"

ActorUrn = Annotated[str, StringConstraints(pattern=rf"^urn:actor:{_ID}$")]
RoleUrn = Annotated[str, StringConstraints(pattern=rf"^urn:role:{_ID}$")]
ResourceUrn = Annotated[str, StringConstraints(pattern=rf"^urn:resource:{_ID}:{_ID}:{_ID}$")]


class Action(str, Enum):
    """Actions a role can be granted on a resource.

    The spec lists READ/WRITE/EXECUTE in the graph section and READ/WRITE/ADMIN
    in the API section, so all four values are accepted for now.
    """

    READ = "READ"
    WRITE = "WRITE"
    EXECUTE = "EXECUTE"
    ADMIN = "ADMIN"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Actor(_Strict):
    urn: ActorUrn
    name: str = Field(min_length=1)
    department: str = Field(min_length=1)
    roles: list[RoleUrn] = Field(default_factory=list)


class Role(_Strict):
    urn: RoleUrn
    name: str = Field(min_length=1)
    inherits_from: list[RoleUrn] = Field(default_factory=list)


class Grant(_Strict):
    """A policy line: the role is granted an action on a resource."""

    role: RoleUrn
    resource: ResourceUrn
    action: Action


class IamDataset(_Strict):
    """A full batch of IAM data, the body of POST /api/v1/iam/ingest."""

    users: list[Actor] = Field(default_factory=list)
    roles: list[Role] = Field(default_factory=list)
    policies: list[Grant] = Field(default_factory=list)
