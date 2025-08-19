"""
Nox configuration for Concordia CLI.

This file defines test sessions and automation tasks using nox.
Run 'nox --list' to see all available sessions.
"""

import nox

# Configure nox to use uv as the backend for faster installs
VENV_BACKEND = "uv"
# Supported Python versions
PYTHON_VERSIONS = ["3.11", "3.12", "3.13"]
DEFAULT_PYTHON = "3.11"

# Common pytest arguments
PYTEST_ARGS = ["-v", "--tb=short"]


@nox.session(python=DEFAULT_PYTHON, venv_backend=VENV_BACKEND)
def format(session):
    """Run ruff formatting."""
    session.install("ruff")
    session.run("ruff", "format", ".")


@nox.session(python=DEFAULT_PYTHON, venv_backend=VENV_BACKEND)
def format_check(session):
    """Check ruff formatting without making changes."""
    session.install("ruff")
    session.run("ruff", "format", "--check", ".")


@nox.session(python=DEFAULT_PYTHON, venv_backend=VENV_BACKEND)
def lint(session):
    """Run ruff linting."""
    session.install("ruff")
    session.run("ruff", "check", ".")


@nox.session(python=DEFAULT_PYTHON, venv_backend=VENV_BACKEND)
def lint_fix(session):
    """Run ruff linting with auto-fix."""
    session.install("ruff")
    session.run("ruff", "check", "--fix", ".")


@nox.session(python=DEFAULT_PYTHON, venv_backend=VENV_BACKEND)
def type_check(session):
    """Run mypy type checking."""
    session.install("-r", "requirements.txt", "-r", "requirements-dev.txt")
    session.run(
        "mypy",
        "actions/",
        "--ignore-missing-imports",
        "--no-strict-optional",
    )


@nox.session(python=PYTHON_VERSIONS, venv_backend=VENV_BACKEND)
def unit(session):
    """Run unit tests only."""
    session.install("-r", "requirements.txt", "-r", "requirements-dev.txt")
    session.run(
        "pytest",
        "-o",
        "addopts=",  # Clear addopts from pytest.ini
        "tests/unit/",
        *PYTEST_ARGS,
    )


@nox.session(python=PYTHON_VERSIONS, venv_backend=VENV_BACKEND)
def integration(session):
    """Run integration tests only."""
    session.install("-r", "requirements.txt", "-r", "requirements-dev.txt")
    session.run(
        "pytest",
        "-o",
        "addopts=",  # Clear addopts from pytest.ini
        "tests/integration/",
        *PYTEST_ARGS,
    )


@nox.session(python=PYTHON_VERSIONS, venv_backend=VENV_BACKEND)
def test(session):
    """Run all tests."""
    session.install("-r", "requirements.txt", "-r", "requirements-dev.txt")
    session.run("pytest", "tests/", *PYTEST_ARGS)


@nox.session(python=DEFAULT_PYTHON, venv_backend=VENV_BACKEND)
def coverage(session):
    """Run tests with coverage report."""
    session.install("-r", "requirements.txt", "-r", "requirements-dev.txt")
    session.run(
        "pytest",
        "tests/",
        "--cov=actions",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        "--cov-report=xml:coverage.xml",
        "--cov-fail-under=70",
        *PYTEST_ARGS,
    )


@nox.session(python=DEFAULT_PYTHON, venv_backend=VENV_BACKEND)
def fast(session):
    """Run tests with minimal output for quick feedback."""
    session.install("-r", "requirements.txt", "-r", "requirements-dev.txt")
    session.run("pytest", "tests/", "-q", "--tb=short")


@nox.session(python=DEFAULT_PYTHON, venv_backend=VENV_BACKEND)
def security(session):
    """Run security checks with safety."""
    session.install("safety")
    session.run("safety", "check", "--output", "json", "--continue-on-error")


@nox.session(python=DEFAULT_PYTHON, venv_backend=VENV_BACKEND)
def ci(session):
    """Run CI-equivalent checks (format, lint, type check, coverage)."""
    session.install("-r", "requirements.txt", "-r", "requirements-dev.txt")

    # Format check
    session.run("ruff", "format", "--check", ".")

    # Lint check
    session.run("ruff", "check", ".")
    # Type check
    session.run(
        "mypy",
        "actions/",
        "--ignore-missing-imports",
        "--no-strict-optional",
    )

    # Tests with coverage
    session.run(
        "pytest",
        "tests/",
        "--cov=actions",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        "--cov-report=xml:coverage.xml",
        "--cov-fail-under=70",
        *PYTEST_ARGS,
    )


@nox.session(python=DEFAULT_PYTHON, venv_backend=VENV_BACKEND)
def all(session):
    """Run comprehensive test suite (format, lint, type check, unit, integration, coverage, security)."""
    session.install("-r", "requirements.txt", "-r",
                    "requirements-dev.txt", "safety")

    # Format check
    session.run("ruff", "format", "--check", ".")

    # Lint check
    session.run("ruff", "check", ".")

    # Type check
    session.run(
        "mypy",
        "actions/",
        "--ignore-missing-imports",
        "--no-strict-optional",
    )

    # Unit tests
    session.run("pytest", "-o", "addopts=", "tests/unit/", *PYTEST_ARGS)

    # Integration tests
    session.run("pytest", "-o", "addopts=", "tests/integration/", *PYTEST_ARGS)

    # Coverage
    session.run(
        "pytest",
        "tests/",
        "--cov=actions",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        "--cov-report=xml:coverage.xml",
        "--cov-fail-under=70",
        *PYTEST_ARGS,
    )

    # Security check
    session.run("safety", "check", "--output", "json", "--continue-on-error")


@nox.session(python=DEFAULT_PYTHON, venv_backend=VENV_BACKEND)
def lint_tests(session):
    """Run linting on test files."""
    session.install("ruff")
    session.run("ruff", "check", "tests/")


@nox.session(python=DEFAULT_PYTHON, venv_backend=VENV_BACKEND)
def docs(session):
    """Build documentation (placeholder for future docs)."""
    session.log("Documentation build not yet implemented")


# Configure nox defaults
nox.options.error_on_external_run = True
nox.options.reuse_existing_virtualenvs = True
