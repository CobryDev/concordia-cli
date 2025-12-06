"""
Shared LookML naming validation and sanitization utilities.

Ensures generated view and field names only contain characters that are
supported by the LookML parser while allowing configurable replacements
for unsupported characters.
"""

import re
from typing import Optional

ALLOWED_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")


class LookMLNameValidator:
    """Validate and sanitize LookML identifiers."""

    allowed_pattern = ALLOWED_NAME_PATTERN

    def __init__(self, replacements: Optional[dict[str, str]] = None):
        """
        Initialize the validator.

        Args:
            replacements: Optional mapping of characters to replace before validation.
        """
        self.replacements = replacements or {}

    @classmethod
    def ensure_allowed_characters(cls, candidate: str, context: str, raw_value: Optional[str] = None) -> None:
        """
        Ensure a candidate name only contains allowed characters.

        Args:
            candidate: The processed name to validate.
            context: Description of what is being validated (e.g., 'view', 'dimension').
            raw_value: Original value for clearer error messages.

        Raises:
            ValueError: If the name is empty or contains unsupported characters.
        """
        label = raw_value if raw_value is not None else candidate
        if not candidate or not candidate.strip():
            raise ValueError(f"{context.capitalize()} name cannot be empty")

        if not cls.allowed_pattern.match(candidate):
            invalid_chars = sorted(
                {ch for ch in candidate if not (ch.isalnum() or ch == "_")})
            if invalid_chars:
                invalid_display = "', '".join(invalid_chars)
                detail = f"invalid character(s): '{invalid_display}'"
            else:
                detail = "contains unsupported characters"

            raise ValueError(
                f"Invalid {context} name '{label}': {detail}. "
                "Only letters, numbers, and underscores are allowed. "
                "Configure naming_conventions.character_replacements to map unsupported characters."
            )

    def sanitize(self, raw_name: str, context: str) -> str:
        """
        Apply replacements and validate the resulting name.

        Args:
            raw_name: Name before replacements.
            context: Description of the identifier being sanitized.

        Returns:
            Sanitized and validated identifier.

        Raises:
            ValueError: If the name remains invalid after replacements.
        """
        if raw_name is None:
            raise ValueError(f"{context.capitalize()} name cannot be empty")

        candidate = raw_name.strip()
        for target, replacement in self.replacements.items():
            candidate = candidate.replace(target, replacement)

        self.ensure_allowed_characters(candidate, context, raw_value=raw_name)
        return candidate
