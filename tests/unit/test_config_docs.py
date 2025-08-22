"""Test configuration documentation generation."""

from actions.utils.config_docs import generate_config_docs, save_config_docs


class TestConfigDocs:
    """Test configuration documentation generation functions."""

    def test_generate_config_docs_returns_string(self):
        """Test that generate_config_docs returns a non-empty string."""
        docs = generate_config_docs()

        assert isinstance(docs, str)
        assert len(docs) > 0
        assert "# Concordia Configuration Guide" in docs

    def test_generate_config_docs_includes_expected_sections(self):
        """Test that generated docs include expected sections."""
        docs = generate_config_docs()

        # Check for main sections
        assert "## Overview" in docs
        assert "## Configuration Validation" in docs
        assert "## Complete Configuration Example" in docs
        assert "## BigQuery Connection Configuration" in docs
        assert "## Looker Project Configuration" in docs
        assert "## Model Generation Rules" in docs
        assert "## Troubleshooting" in docs

    def test_generate_config_docs_includes_yaml_examples(self):
        """Test that generated docs include YAML configuration examples."""
        docs = generate_config_docs()

        # Check for YAML blocks
        assert "```yaml" in docs
        assert "connection:" in docs
        assert "looker:" in docs
        assert "model_rules:" in docs

    def test_save_config_docs_creates_file(self, tmp_path):
        """Test that save_config_docs creates a file with documentation."""
        output_file = tmp_path / "test_config.md"
        save_config_docs(str(output_file))

        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")
        assert "# Concordia Configuration Guide" in content
