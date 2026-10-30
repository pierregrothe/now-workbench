"""Pydantic models for ServiceNow Fluent SDK schema definitions and diffs."""

from pydantic import BaseModel, ConfigDict, Field


class FluentColumnDef(BaseModel):
    """Definition of a table column or field in a ServiceNow Fluent schema."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    label: str = ""
    column_type: str = "string"
    reference: str | None = None
    mandatory: bool = False
    max_length: int | None = None


class FluentTableSchema(BaseModel):
    """Schema of a table declared via the ServiceNow Fluent SDK (Table(...))."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    label: str
    columns: list[FluentColumnDef] = Field(default_factory=list)
    raw_source: str = ""


class FluentSchemaDiff(BaseModel):
    """Structural diff between two ServiceNow Fluent schema definitions."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    added_tables: list[str] = Field(default_factory=list)
    removed_tables: list[str] = Field(default_factory=list)
    modified_tables: dict[str, list[str]] = Field(default_factory=dict)
    identical: bool = True
