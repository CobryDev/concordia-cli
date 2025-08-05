#!/usr/bin/env python3
"""
Test runner script for Concordia CLI.

This script provides convenient commands for running tests with different
configurations and generating reports.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# Handle Windows encoding issues with Unicode emojis


def setup_encoding():
    """Set up proper encoding for cross-platform compatibility."""
    try:
        # Try to set UTF-8 encoding on Windows
        if sys.platform == 'win32':
            import codecs
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
    except (AttributeError, UnicodeError):
        # Fallback for older Python versions or encoding issues
        pass


def safe_print(message):
    """Print message with fallback for encoding issues."""
    try:
        print(message)
    except UnicodeEncodeError:
        # Replace emojis with ASCII alternatives for Windows compatibility
        emoji_map = {
            '🔄': '[RUNNING]',
            '✅': '[PASS]',
            '❌': '[FAIL]',
            '📊': '[REPORT]',
            '🔍': '[CHECK]',
            '📝': '[NOTE]',
            '⚠️': '[WARN]',
            '🔧': '[SETUP]',
            '🧪': '[TEST]',
            '📋': '[SUITE]',
            '🎉': '[SUCCESS]',
            '💥': '[ERROR]'
        }
        safe_message = message
        for emoji, replacement in emoji_map.items():
            safe_message = safe_message.replace(emoji, replacement)
        print(safe_message)


# Initialize encoding setup
setup_encoding()


def run_command(cmd, description):
    """Run a command and handle errors."""
    safe_print(f"\n🔄 {description}")
    print(f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        safe_print(f"✅ {description} completed successfully")
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        safe_print(f"❌ {description} failed with exit code {e.returncode}")
        return False
    except FileNotFoundError:
        safe_print(
            f"❌ Command not found. Make sure pytest is installed: pip install -r requirements.txt")
        return False


def run_unit_tests():
    """Run unit tests only."""
    cmd = ["pytest", "tests/unit/", "-v"]
    return run_command(cmd, "Running unit tests")


def run_integration_tests():
    """Run integration tests only."""
    cmd = ["pytest", "tests/integration/", "-v"]
    return run_command(cmd, "Running integration tests")


def run_all_tests():
    """Run all tests."""
    cmd = ["pytest", "tests/", "-v"]
    return run_command(cmd, "Running all tests")


def run_tests_with_coverage():
    """Run tests with coverage report."""
    cmd = [
        "pytest",
        "tests/",
        "--cov=actions",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        "--cov-report=xml:coverage.xml",
        "--cov-fail-under=70",
        "-v"
    ]
    success = run_command(cmd, "Running tests with coverage")

    if success:
        safe_print("\n📊 Coverage report generated:")
        print("  - Terminal: Coverage summary displayed above")
        print("  - HTML: Open htmlcov/index.html in your browser")
        print("  - XML: coverage.xml for CI integration")

    return success


def run_specific_test(test_path):
    """Run a specific test file or test."""
    cmd = ["pytest", test_path, "-v"]
    return run_command(cmd, f"Running specific test: {test_path}")


def run_tests_fast():
    """Run tests with minimal output for quick feedback."""
    cmd = ["pytest", "tests/", "-q", "--tb=short"]
    return run_command(cmd, "Running fast tests")


def lint_tests():
    """Run linting on test files."""
    safe_print("\n🔍 Checking test code quality...")

    # Check if flake8 is available
    try:
        subprocess.run(["flake8", "--version"],
                       check=True, capture_output=True)
        cmd = ["flake8", "tests/", "--max-line-length=100", "--ignore=E501,W503"]
        return run_command(cmd, "Linting test files")
    except (subprocess.CalledProcessError, FileNotFoundError):
        safe_print("📝 flake8 not available, skipping linting")
        print("   Install with: pip install flake8")
        return True


def check_dependencies():
    """Check if test dependencies are installed."""
    safe_print("\n🔍 Checking test dependencies...")

    required_packages = ["pytest", "pytest-cov", "pytest-mock"]
    missing_packages = []

    for package in required_packages:
        try:
            subprocess.run([sys.executable, "-c", f"import {package.replace('-', '_')}"],
                           check=True, capture_output=True)
            safe_print(f"  ✅ {package}")
        except subprocess.CalledProcessError:
            safe_print(f"  ❌ {package}")
            missing_packages.append(package)

    if missing_packages:
        safe_print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        print("   Install with: pip install -r requirements.txt")
        return False

    safe_print("✅ All test dependencies are installed")
    return True


def setup_test_environment():
    """Set up the test environment."""
    safe_print("🔧 Setting up test environment...")

    # Ensure test directories exist
    test_dirs = ["tests/unit", "tests/integration", "tests/fixtures"]
    for test_dir in test_dirs:
        Path(test_dir).mkdir(parents=True, exist_ok=True)
        safe_print(f"  ✅ {test_dir}")

    # Check Python path
    project_root = Path(__file__).parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
        safe_print(f"  ✅ Added {project_root} to Python path")

    return True


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Concordia CLI Test Runner")
    parser.add_argument("command", nargs="?", default="all",
                        help="Test command to run")
    parser.add_argument(
        "--test", "-t", help="Specific test file or test to run")
    parser.add_argument("--no-deps", action="store_true",
                        help="Skip dependency check")

    args = parser.parse_args()

    safe_print("🧪 Concordia CLI Test Runner")
    print("=" * 40)

    # Setup environment
    if not setup_test_environment():
        sys.exit(1)

    # Check dependencies unless skipped
    if not args.no_deps and not check_dependencies():
        sys.exit(1)

    # Handle specific test
    if args.test:
        success = run_specific_test(args.test)
        sys.exit(0 if success else 1)

    # Handle commands
    command = args.command.lower()

    if command == "unit":
        success = run_unit_tests()
    elif command == "integration":
        success = run_integration_tests()
    elif command == "coverage":
        success = run_tests_with_coverage()
    elif command == "fast":
        success = run_tests_fast()
    elif command == "lint":
        success = lint_tests()
    elif command == "all":
        safe_print("\n📋 Running comprehensive test suite...")
        success = True
        success &= run_unit_tests()
        success &= run_integration_tests()
        success &= run_tests_with_coverage()
        success &= lint_tests()
    else:
        safe_print(f"❌ Unknown command: {command}")
        print("\nAvailable commands:")
        print("  all         - Run all tests with coverage and linting")
        print("  unit        - Run unit tests only")
        print("  integration - Run integration tests only")
        print("  coverage    - Run tests with coverage report")
        print("  fast        - Run tests with minimal output")
        print("  lint        - Lint test files")
        print("\nExamples:")
        print("  python run_tests.py")
        print("  python run_tests.py unit")
        print("  python run_tests.py --test tests/unit/test_field_utils.py")
        sys.exit(1)

    if success:
        safe_print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        safe_print("\n💥 Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
