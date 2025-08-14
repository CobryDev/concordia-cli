"""
Safe printing utilities for handling Unicode encoding issues.
"""

from typing import Any

import click


def safe_echo(message: Any, **kwargs) -> None:
    """
    Safely print a message using click.echo with fallback for Unicode encoding issues.

    This function handles UnicodeEncodeError exceptions that can occur on systems
    with limited Unicode support (particularly Windows terminals) by providing
    ASCII alternatives for emoji characters.

    Args:
        message: The message to print
        **kwargs: Additional arguments to pass to click.echo
    """
    try:
        click.echo(message, **kwargs)
    except UnicodeEncodeError:  # pragma: no cover
        # Replace emojis with ASCII alternatives for compatibility
        emoji_map = {
            "🔄": "[RUNNING]",
            "✅": "[PASS]",
            "❌": "[FAIL]",
            "📊": "[REPORT]",
            "🔍": "[SCAN]",
            "📝": "[NOTE]",
            "⚠️": "[WARN]",
            "🔧": "[SETUP]",
            "🧪": "[TEST]",
            "📋": "[INIT]",
            "🎉": "[SUCCESS]",
            "💥": "[ERROR]",
            "🚀": "[COMPLETE]",
        }

        safe_message = str(message)
        for emoji, replacement in emoji_map.items():
            safe_message = safe_message.replace(emoji, replacement)

        click.echo(safe_message, **kwargs)
