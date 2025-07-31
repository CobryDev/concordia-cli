"""
Unit tests for the help module.
"""

import pytest
from unittest.mock import patch
from actions.help.help import show_help


class TestHelp:
    """Test help functionality."""

    @patch('actions.help.help.click.echo')
    def test_show_help(self, mock_echo):
        """Test show_help displays the correct help text."""
        show_help()

        # Verify click.echo was called once
        mock_echo.assert_called_once()

        # Get the help text that was passed to click.echo
        help_text = mock_echo.call_args[0][0]

        # Verify key sections are present
        assert "Concordia CLI" in help_text
        assert "COMMANDS:" in help_text
        assert "init" in help_text
        assert "looker" in help_text
        assert "generate" in help_text
        assert "EXAMPLES:" in help_text
        assert "concordia init" in help_text
        assert "concordia looker generate" in help_text
