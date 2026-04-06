from pathlib import Path
from typing import Any

import lkml

from ..models.config import ConcordiaConfig
from ..models.lookml import LookMLProject, LookMLView
from ..models.metadata import MetadataCollection, TableMetadata
from .lookml_measure_module import LookMLMeasureGenerator
from .lookml_module import LookMLViewGenerator


class DuplicateViewNameError(Exception):
    """Raised when multiple tables generate views with the same name."""

    def __init__(self, view_name: str, conflicting_tables: list[dict[str, str]]):
        """
        Initialize the error with view name and conflicting table information.

        Args:
            view_name: The duplicate view name
            conflicting_tables: List of dicts with keys 'table_id', 'dataset_id', 'project_id'
        """
        self.view_name = view_name
        self.conflicting_tables = conflicting_tables
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format the error message with details about conflicting tables."""
        lines = [
            f"Duplicate view name '{self.view_name}' detected. "
            f"The following {len(self.conflicting_tables)} table(s) would generate views with the same name:",
            "",
        ]
        for table in self.conflicting_tables:
            full_table_name = f"{table['project_id']}.{table['dataset_id']}.{table['table_id']}"
            lines.append(f"  • {full_table_name}")
        lines.append("")
        lines.append(
            "To resolve this, you can:"
            "\n  1. Use view_prefix or view_suffix in your naming_conventions to differentiate views"
            "\n  2. Rename one of the conflicting tables in BigQuery"
            "\n  3. Exclude one of the tables from generation"
        )
        return "\n".join(lines)


class LookMLGenerator:
    """
    Generates LookML view files from BigQuery table schemas using dictionary-based approach.
    Following the droughty pattern of treating LookML as data structures.
    """

    def __init__(self, config: ConcordiaConfig):
        """
        Initialize the LookML generator.

        Args:
            config: The loaded ConcordiaConfig object
        """
        self.config = config
        self.model_rules = config.model_rules
        self.looker_config = config.looker
        self.connection_name = self.looker_config.connection

        # Initialize the modular generators
        self.view_generator = LookMLViewGenerator(config)
        self.measure_generator = LookMLMeasureGenerator(config)

    def generate_view_for_table_metadata(self, table_metadata: TableMetadata) -> LookMLView:
        """
        Generate LookML view for a single table using metadata.

        Args:
            table_metadata: TableMetadata object from MetadataExtractor

        Returns:
            LookMLView object containing the view definition
        """
        # Generate the base view
        view_dict = self.view_generator.generate_view_dict(table_metadata)

        # Convert to LookMLView object (if needed)
        # For now, we'll create a simple LookMLView from the dict
        view_name = list(view_dict["view"].keys())[0]
        view_data = view_dict["view"][view_name]

        # Build LookMLView without connection/description (not included in base views)
        lookml_view = LookMLView(name=view_name, sql_table_name=view_data["sql_table_name"])

        # Bring over dimensions from the base view dict
        if "dimension" in view_data:
            from ..models.lookml import Dimension, DimensionType

            for dim_dict in view_data["dimension"]:
                for dim_name, dim_values in dim_dict.items():
                    dim_obj = Dimension(
                        name=dim_name,
                        type=DimensionType(dim_values.get("type", "string")),
                        sql=dim_values.get("sql"),
                        description=dim_values.get("description"),
                        hidden=dim_values.get("hidden") == "yes",
                        primary_key=dim_values.get("primary_key") == "yes",
                    )
                    lookml_view.add_dimension(dim_obj)

        # Bring over dimension groups from the base view dict
        if "dimension_group" in view_data:
            from ..models.lookml import DimensionGroup, DimensionGroupType

            for group_dict in view_data["dimension_group"]:
                for group_name, group_values in group_dict.items():
                    group_obj = DimensionGroup(
                        name=group_name,
                        type=DimensionGroupType(group_values.get("type", "time")),
                        sql=group_values.get("sql"),
                        description=group_values.get("description"),
                        timeframes=group_values.get("timeframes"),
                        datatype=group_values.get("datatype"),
                    )
                    lookml_view.add_dimension_group(group_obj)

        # Bring over drill field set definition if present
        if "set" in view_data:
            # Preserve the exact structure to be serialized by lkml
            lookml_view.additional_params.update({"set": view_data["set"]})

        # Generate measures and add them to the view
        measures = self.measure_generator.generate_measures_for_view(table_metadata)

        # Convert measure dictionaries to Measure objects
        from ..models.lookml import Measure, MeasureType

        for measure_dict in measures:
            for measure_name, measure_data in measure_dict.items():
                measure_obj = Measure(
                    name=measure_name,
                    type=MeasureType(measure_data["type"]),
                    sql=measure_data.get("sql"),
                    description=measure_data.get("description"),
                    hidden=measure_data.get("hidden") == "yes",
                )
                lookml_view.add_measure(measure_obj)

        return lookml_view

    def generate_view_for_table(self, table_metadata: TableMetadata) -> str:
        """
        Generate LookML view content for a single table (backward compatibility).

        Args:
            table_metadata: TableMetadata object

        Returns:
            String containing the LookML view definition
        """
        lookml_view = self.generate_view_for_table_metadata(table_metadata)
        view_dict = lookml_view.to_dict()

        result = lkml.dump(view_dict)
        if result is None:
            return ""

        self._validate_lookml_content(result, f"view '{lookml_view.name}'")
        return result

    def generate_complete_lookml_project(self, tables_metadata: MetadataCollection) -> LookMLProject:
        """
        Generate a complete LookML project with views only.

        Args:
            tables_metadata: MetadataCollection containing table metadata

        Returns:
            LookMLProject containing the complete project

        Raises:
            DuplicateViewNameError: If multiple tables would generate views with the same name
        """
        project = LookMLProject()
        view_name_to_tables: dict[str, list[dict[str, str]]] = {}

        # First pass: generate all views and collect view names
        for table_metadata in tables_metadata.get_all_tables():
            lookml_view = self.generate_view_for_table_metadata(table_metadata)
            view_name = lookml_view.name

            # Track which tables generate each view name
            if view_name not in view_name_to_tables:
                view_name_to_tables[view_name] = []
            view_name_to_tables[view_name].append(
                {
                    "table_id": table_metadata.table_id,
                    "dataset_id": table_metadata.dataset_id,
                    "project_id": table_metadata.project_id,
                }
            )

        # Check for duplicate view names
        for view_name, tables in view_name_to_tables.items():
            if len(tables) > 1:
                raise DuplicateViewNameError(view_name, tables)

        # Second pass: add all views to project (no duplicates at this point)
        for table_metadata in tables_metadata.get_all_tables():
            lookml_view = self.generate_view_for_table_metadata(table_metadata)
            project.add_view(lookml_view)

        return project

    def _validate_lookml_content(self, content: str, context: str) -> None:
        """
        Validate that generated LookML can be parsed by the lkml library.

        Args:
            content: LookML content as a string.
            context: Description of the content being validated.

        Raises:
            ValueError: If lkml fails to parse the generated content.
        """
        try:
            if hasattr(lkml, "loads"):
                lkml.loads(content)
            elif hasattr(lkml, "load"):
                lkml.load(content)
            else:
                return
        except Exception as exc:
            # If parsing fails, warn but do not block generation to remain backward compatible
            click.echo(f"⚠️  Warning: Generated LookML for {context} could not be validated: {exc}")


class LookMLFileWriter:
    """
    Handles writing LookML files using the lkml library for proper serialization.
    Following the droughty pattern of treating LookML as data structures.
    """

    def __init__(self, config: ConcordiaConfig):
        """
        Initialize the file writer.

        Args:
            config: The loaded ConcordiaConfig object
        """
        self.config = config
        self.looker_config = config.looker

    def write_views_file(self, view_contents: list[str]) -> str:
        """
        Write a single LookML file containing all generated views(backward compatibility).

        Args:
            view_contents: List of generated LookML view content strings

        Returns:
            Path to the written file
        """
        project_path = Path(self.looker_config.project_path)
        views_path = self.looker_config.views_path

        # views_path is the exact file path relative to project_path
        file_path = project_path / views_path

        # Create the directory structure if it doesn't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Add warning comment to the beginning of the file
        warning_comment = (
            "# Do not edit this file. It's been pre-generated using 'concordia-cli'.\n"
            "# Use this as a base view to refine from. All edits will be over-written on next generation.\n\n"
        )

        # Combine all view contents into a single file
        combined_content = "\n\n".join(view_contents)

        # Write the file
        with open(file_path, "w") as f:
            f.write(warning_comment)
            f.write(combined_content)

        return str(file_path)

    def write_lookml_dict_file(self, lookml_dict: dict[str, Any], file_suffix: str = "views") -> str:
        """
        Write a LookML file from a dictionary using the lkml library.

        Args:
            lookml_dict: Dictionary containing LookML structure
            file_suffix: Suffix for the file name(e.g., "views")

        Returns:
            Path to the written file
        """
        project_path = Path(self.looker_config.project_path)

        # Generate file name
        if file_suffix == "views":
            file_path = project_path / self.looker_config.views_path
        else:
            # For any other file types, generate a new file name using views_path as base
            base_name = Path(self.looker_config.views_path).stem
            base_dir = Path(self.looker_config.views_path).parent
            file_path = project_path / base_dir / f"{base_name}_{file_suffix}.view.lkml"

        # Create the directory structure if it doesn't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Use lkml library to dump the dictionary to LookML format
        lookml_content = lkml.dump(lookml_dict)

        # Validate that the generated LookML can be parsed
        if lookml_content is not None:
            self._validate_lookml_content(lookml_content, f"{file_suffix} file")

        # Add warning comment to the beginning of the file
        warning_comment = (
            "# Do not edit this file. It's been pre-generated using 'concordia-cli'.\n"
            "# Use this as a base view to refine from. All edits will be over-written on next generation.\n\n"
        )

        # Write the file
        with open(file_path, "w") as f:
            f.write(warning_comment)
            f.write(lookml_content if lookml_content is not None else "")

        return str(file_path)

    def write_views_dict_file(self, views_dict: dict[str, Any]) -> str:
        """
        Write views from dictionary to file.

        Args:
            views_dict: Dictionary containing view definitions

        Returns:
            Path to the written file
        """
        return self.write_lookml_dict_file(views_dict, "views")

    def write_complete_project(self, project_dict: dict[str, Any]) -> list[str]:
        """
        Write a complete LookML project with views only.

        Args:
            project_dict: Dictionary containing the complete project structure

        Returns:
            List of paths to the written files
        """
        written_files = []

        # Write views file
        if "view" in project_dict:
            views_file = self.write_lookml_dict_file({"view": project_dict["view"]}, "views")
            written_files.append(views_file)

        return written_files

    def _validate_lookml_content(self, content: str, context: str) -> None:
        """
        Validate that generated LookML content can be parsed.

        Args:
            content: LookML content as a string.
            context: Description of what is being validated.

        Raises:
            ValueError: If lkml fails to parse the content.
        """
        try:
            if hasattr(lkml, "loads"):
                lkml.loads(content)
            elif hasattr(lkml, "load"):
                lkml.load(content)
            else:
                return
        except Exception as exc:
            click.echo(f"⚠️  Warning: Generated LookML for {context} could not be validated: {exc}")
