"""
Pydantic models for LookML components.

These models provide type safety for LookML structures that are currently
represented as nested dictionaries, enabling better validation and code clarity.
"""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class DimensionType(str, Enum):
    """Valid LookML dimension types."""

    STRING = "string"
    NUMBER = "number"
    YESNO = "yesno"
    TIER = "tier"
    LOCATION = "location"
    ZIPCODE = "zipcode"


class DimensionGroupType(str, Enum):
    """Valid LookML dimension group types."""

    TIME = "time"
    DURATION = "duration"


class MeasureType(str, Enum):
    """Valid LookML measure types."""

    COUNT = "count"
    COUNT_DISTINCT = "count_distinct"
    SUM = "sum"
    AVERAGE = "average"
    MIN = "min"
    MAX = "max"
    MEDIAN = "median"
    PERCENTILE = "percentile"
    LIST = "list"
    NUMBER = "number"


class Dimension(BaseModel):
    """LookML dimension definition."""

    name: str = Field(description="Dimension name")
    type: DimensionType = Field(description="Dimension type")
    sql: Optional[str] = Field(default=None, description="Custom SQL expression")
    description: Optional[str] = Field(default=None, description="Dimension description")
    label: Optional[str] = Field(default=None, description="Display label")
    hidden: bool = Field(default=False, description="Whether dimension is hidden")
    primary_key: bool = Field(default=False, description="Whether this is a primary key")
    group_label: Optional[str] = Field(default=None, description="Group label for organization")
    value_format: Optional[str] = Field(default=None, description="Value formatting")
    drill_fields: Optional[list[str]] = Field(default=None, description="Fields to drill into")

    # Allow additional LookML parameters
    additional_params: dict[str, Any] = Field(default_factory=dict, description="Additional LookML parameters")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        """Ensure name is valid."""
        if not v or not v.strip():
            raise ValueError("Dimension name cannot be empty")
        return v.strip()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for LookML serialization (flat form)."""
        result: dict[str, Any] = {
            "name": self.name,
            "type": self.type.value,
        }

        # Add optional fields
        if self.sql:
            result["sql"] = self.sql
        if self.description:
            result["description"] = self.description
        if self.label:
            result["label"] = self.label
        if self.hidden:
            result["hidden"] = "yes"
        if self.primary_key:
            result["primary_key"] = "yes"
        if self.group_label:
            result["group_label"] = self.group_label
        if self.value_format:
            result["value_format"] = self.value_format
        if self.drill_fields:
            result["drill_fields"] = str(self.drill_fields)

        # Add any additional parameters
        result.update(self.additional_params)

        return result


class DimensionGroup(BaseModel):
    """LookML dimension group definition."""

    name: str = Field(description="Dimension group name")
    type: DimensionGroupType = Field(description="Dimension group type")
    sql: Optional[str] = Field(default=None, description="Custom SQL expression")
    description: Optional[str] = Field(default=None, description="Description")
    label: Optional[str] = Field(default=None, description="Display label")
    timeframes: Optional[list[str]] = Field(default=None, description="Available timeframes")
    convert_tz: bool = Field(default=True, description="Whether to convert timezone")
    datatype: Optional[str] = Field(default=None, description="Data type for time fields")
    intervals: Optional[list[str]] = Field(default=None, description="Duration intervals")

    # Allow additional LookML parameters
    additional_params: dict[str, Any] = Field(default_factory=dict, description="Additional LookML parameters")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        """Ensure name is valid."""
        if not v or not v.strip():
            raise ValueError("Dimension group name cannot be empty")
        return v.strip()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for LookML serialization (flat form)."""
        result: dict[str, Any] = {
            "name": self.name,
            "type": self.type.value,
        }

        # Add optional fields
        if self.sql:
            result["sql"] = self.sql
        if self.description:
            result["description"] = self.description
        if self.label:
            result["label"] = self.label
        if self.timeframes:
            result["timeframes"] = str(self.timeframes)
        if not self.convert_tz:
            result["convert_tz"] = "no"
        if self.datatype:
            result["datatype"] = self.datatype
        if self.intervals:
            result["intervals"] = str(self.intervals)

        # Add any additional parameters
        result.update(self.additional_params)

        return result


class Measure(BaseModel):
    """LookML measure definition."""

    name: str = Field(description="Measure name")
    type: MeasureType = Field(description="Measure type")
    sql: Optional[str] = Field(default=None, description="Custom SQL expression")
    description: Optional[str] = Field(default=None, description="Measure description")
    label: Optional[str] = Field(default=None, description="Display label")
    hidden: bool = Field(default=False, description="Whether measure is hidden")
    group_label: Optional[str] = Field(default=None, description="Group label for organization")
    value_format: Optional[str] = Field(default=None, description="Value formatting")
    drill_fields: Optional[list[str]] = Field(default=None, description="Fields to drill into")
    filters: Optional[dict[str, str]] = Field(default=None, description="Filter conditions")

    # Allow additional LookML parameters
    additional_params: dict[str, Any] = Field(default_factory=dict, description="Additional LookML parameters")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        """Ensure name is valid."""
        if not v or not v.strip():
            raise ValueError("Measure name cannot be empty")
        return v.strip()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for LookML serialization (flat form)."""
        result: dict[str, Any] = {
            "name": self.name,
            "type": self.type.value,
        }

        # Add optional fields
        if self.sql:
            result["sql"] = self.sql
        if self.description:
            result["description"] = self.description
        if self.label:
            result["label"] = self.label
        if self.hidden:
            result["hidden"] = "yes"
        if self.group_label:
            result["group_label"] = self.group_label
        if self.value_format:
            result["value_format"] = self.value_format
        if self.drill_fields:
            result["drill_fields"] = str(self.drill_fields)
        if self.filters:
            result["filters"] = str(self.filters)

        # Add any additional parameters
        result.update(self.additional_params)

        return result


class LookMLView(BaseModel):
    """LookML view definition."""

    name: str = Field(description="View name")
    sql_table_name: str = Field(description="SQL table name")
    connection: Optional[str] = Field(default=None, description="Connection name")
    description: Optional[str] = Field(default=None, description="View description")
    dimensions: list[Dimension] = Field(default_factory=list, description="View dimensions")
    dimension_groups: list[DimensionGroup] = Field(default_factory=list, description="View dimension groups")
    measures: list[Measure] = Field(default_factory=list, description="View measures")
    drill_fields: Optional[list[str]] = Field(default=None, description="Default drill fields")

    # Allow additional LookML parameters
    additional_params: dict[str, Any] = Field(default_factory=dict, description="Additional LookML parameters")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        """Ensure name is valid."""
        if not v or not v.strip():
            raise ValueError("View name cannot be empty")
        return v.strip()

    def add_dimension(self, dimension: Dimension) -> None:
        """Add a dimension to the view."""
        self.dimensions.append(dimension)

    def add_dimension_group(self, dimension_group: DimensionGroup) -> None:
        """Add a dimension group to the view."""
        self.dimension_groups.append(dimension_group)

    def add_measure(self, measure: Measure) -> None:
        """Add a measure to the view."""
        self.measures.append(measure)

    def get_dimension_by_name(self, name: str) -> Optional[Dimension]:
        """Get a dimension by name."""
        for dim in self.dimensions:
            if dim.name == name:
                return dim
        return None

    def get_measure_by_name(self, name: str) -> Optional[Measure]:
        """Get a measure by name."""
        for measure in self.measures:
            if measure.name == name:
                return measure
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for LookML serialization as repeated view blocks."""
        view_entry: dict[str, Any] = {
            "name": self.name,
            "sql_table_name": self.sql_table_name,
        }

        # Only include optional fields when provided
        if self.connection:
            view_entry["connection"] = self.connection
        if self.description:
            view_entry["description"] = self.description

        # Add dimensions (flat list form understood by lkml.dump)
        if self.dimensions:
            view_entry["dimension"] = [dim.to_dict() for dim in self.dimensions]

        # Add dimension groups
        if self.dimension_groups:
            view_entry["dimension_group"] = [group.to_dict() for group in self.dimension_groups]

        # Add measures
        if self.measures:
            view_entry["measure"] = [measure.to_dict() for measure in self.measures]

        if self.drill_fields:
            view_entry["drill_fields"] = str(self.drill_fields)

        # Add any additional parameters
        view_entry.update(self.additional_params)

        return {"view": [view_entry]}


class LookMLProject(BaseModel):
    """Complete LookML project definition."""

    views: list[LookMLView] = Field(default_factory=list, description="Project views")

    def add_view(self, view: LookMLView) -> None:
        """Add a view to the project."""
        self.views.append(view)

    def get_view_by_name(self, name: str) -> Optional[LookMLView]:
        """Get a view by name."""
        for view in self.views:
            if view.name == name:
                return view
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for LookML serialization with repeated view blocks."""
        if not self.views:
            return {}

        all_view_entries: list[dict[str, Any]] = []
        for view in self.views:
            view_dict = view.to_dict()
            entries = view_dict.get("view")
            if isinstance(entries, list):
                all_view_entries.extend(entries)

        return {"view": all_view_entries} if all_view_entries else {}
