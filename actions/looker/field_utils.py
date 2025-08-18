"""
Utility functions for field identification and naming conventions.

This module centralizes the logic for identifying primary keys, foreign keys,
and other field-related operations based on naming conventions defined in model rules.
"""

from typing import Optional

from actions.models.config import ModelRules


class FieldIdentifier:
    """
    Utility class for identifying field types based on naming conventions.

    This class centralizes the logic for determining if fields are primary keys,
    foreign keys, or other types based on configured suffix rules.
    """

    def __init__(self, model_rules: ModelRules):
        """
        Initialize with model rules configuration.

        Args:
            model_rules: ModelRules object containing naming conventions and other rules
        """
        self.model_rules = model_rules

    def is_primary_key(self, field_name: str) -> bool:
        """
        Check if a field is a primary key based on naming conventions.

        Args:
            field_name: Name of the field to check

        Returns:
            True if the field is identified as a primary key
        """
        pk_suffix = self.model_rules.naming_conventions.pk_suffix
        return field_name.endswith(pk_suffix) or field_name == "id"

    def is_foreign_key(self, field_name: str) -> bool:
        """
        Check if a field is a foreign key based on naming conventions.

        Args:
            field_name: Name of the field to check

        Returns:
            True if the field is identified as a foreign key
        """
        fk_suffix = self.model_rules.naming_conventions.fk_suffix
        return field_name.endswith(fk_suffix)

    def should_hide_field(self, field_name: str) -> bool:
        """
        Check if a field should be hidden based on configuration.

        Args:
            field_name: Name of the field to check

        Returns:
            True if the field should be hidden
        """
        hide_suffixes = self.model_rules.defaults.hide_fields_by_suffix
        return any(field_name.endswith(suffix) for suffix in hide_suffixes)

    def get_foreign_key_suffix(self) -> str:
        """
        Get the configured foreign key suffix.

        Returns:
            The foreign key suffix from configuration (default: '_fk')
        """
        return self.model_rules.naming_conventions.fk_suffix

    def get_primary_key_suffix(self) -> str:
        """
        Get the configured primary key suffix.

        Returns:
            The primary key suffix from configuration (default: '_pk')
        """
        return self.model_rules.naming_conventions.pk_suffix

    def infer_table_name_from_foreign_key(self, fk_name: str) -> Optional[str]:
        """
        Infer the referenced table name from a foreign key column name.

        Args:
            fk_name: Foreign key column name

        Returns:
            Inferred table name or None if cannot be determined
        """
        fk_suffix = self.get_foreign_key_suffix()

        if fk_name.endswith(fk_suffix):
            # Remove fk_suffix and add s for pluralization
            return fk_name[: -len(fk_suffix)] + "s"
        elif fk_name.endswith("_id"):
            # Keep backward compatibility with _id suffix
            return fk_name[:-3] + "s"  # Remove _id and add s

        return None
