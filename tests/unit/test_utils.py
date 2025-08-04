"""
Tests for utility functions in actions.utils.
"""

import pytest
from unittest.mock import patch, MagicMock
from actions.utils import safe_echo


class TestSafeEcho:
    """Test the safe_echo function."""

    def test_safe_echo_normal_message(self):
        """Test safe_echo with a normal message that should print without issues."""
        with patch('actions.utils.safe_print.click.echo') as mock_echo:
            safe_echo("Hello, world!")
            mock_echo.assert_called_once_with("Hello, world!")

    def test_safe_echo_with_emoji_success(self):
        """Test safe_echo with emoji when Unicode encoding succeeds."""
        with patch('actions.utils.safe_print.click.echo') as mock_echo:
            safe_echo("✅ Success message")
            mock_echo.assert_called_once_with("✅ Success message")

    def test_safe_echo_with_emoji_unicode_error(self):
        """Test safe_echo with emoji when Unicode encoding fails."""
        with patch('actions.utils.safe_print.click.echo') as mock_echo:
            # First call raises UnicodeEncodeError, second call succeeds
            mock_echo.side_effect = [UnicodeEncodeError(
                'utf-8', '✅', 0, 1, 'test'), None]

            safe_echo("✅ Success message")

            # Should be called twice: once with original message, once with fallback
            assert mock_echo.call_count == 2
            mock_echo.assert_any_call("✅ Success message")
            mock_echo.assert_any_call("[PASS] Success message")

    def test_safe_echo_multiple_emojis(self):
        """Test safe_echo with multiple emojis in the message."""
        with patch('actions.utils.safe_print.click.echo') as mock_echo:
            mock_echo.side_effect = [UnicodeEncodeError(
                'utf-8', '✅', 0, 1, 'test'), None]

            safe_echo("✅ Success and 🎉 celebration")

            assert mock_echo.call_count == 2
            mock_echo.assert_any_call("✅ Success and 🎉 celebration")
            mock_echo.assert_any_call(
                "[PASS] Success and [SUCCESS] celebration")

    def test_safe_echo_with_kwargs(self):
        """Test safe_echo passes through additional keyword arguments."""
        with patch('actions.utils.safe_print.click.echo') as mock_echo:
            safe_echo("Test message", err=True, nl=False)
            mock_echo.assert_called_once_with(
                "Test message", err=True, nl=False)

    def test_safe_echo_with_kwargs_and_unicode_error(self):
        """Test safe_echo with kwargs when Unicode encoding fails."""
        with patch('actions.utils.safe_print.click.echo') as mock_echo:
            mock_echo.side_effect = [UnicodeEncodeError(
                'utf-8', '✅', 0, 1, 'test'), None]

            safe_echo("✅ Success", err=True, nl=False)

            assert mock_echo.call_count == 2
            mock_echo.assert_any_call("✅ Success", err=True, nl=False)
            mock_echo.assert_any_call("[PASS] Success", err=True, nl=False)

    def test_safe_echo_non_string_message(self):
        """Test safe_echo with non-string messages."""
        with patch('actions.utils.safe_print.click.echo') as mock_echo:
            safe_echo(123)
            mock_echo.assert_called_once_with(123)

    def test_safe_echo_comprehensive_emoji_mapping(self):
        """Test that all emoji mappings work correctly."""
        emoji_tests = [
            ("🔄 Running", "[RUNNING] Running"),
            ("❌ Failed", "[FAIL] Failed"),
            ("📊 Report", "[REPORT] Report"),
            ("🔍 Scan", "[SCAN] Scan"),
            ("📝 Note", "[NOTE] Note"),
            ("⚠️ Warning", "[WARN] Warning"),
            ("🔧 Setup", "[SETUP] Setup"),
            ("🧪 Test", "[TEST] Test"),
            ("📋 Init", "[INIT] Init"),
            ("🎉 Success", "[SUCCESS] Success"),
            ("💥 Error", "[ERROR] Error"),
            ("🚀 Complete", "[COMPLETE] Complete"),
        ]

        for original, expected in emoji_tests:
            with patch('actions.utils.safe_print.click.echo') as mock_echo:
                mock_echo.side_effect = [UnicodeEncodeError(
                    'utf-8', 'test', 0, 1, 'test'), None]

                safe_echo(original)

                assert mock_echo.call_count == 2
                mock_echo.assert_any_call(original)
                mock_echo.assert_any_call(expected)
