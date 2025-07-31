from typing import List, Dict, Any, Optional
import os
from pathlib import Path
import click
import lkml
from .lookml_base_dict import MetadataExtractor
from .lookml_module import LookMLViewGenerator
from .lookml_measure_module import LookMLMeasureGenerator
from .lookml_explore_module import LookMLExploreGenerator


class LookMLGenerator:
    """
    Generates LookML view files from BigQuery table schemas using dictionary-based approach.
    Following the droughty pattern of treating LookML as data structures.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the LookML generator.

        Args:
            config: The loaded configuration dictionary
        """
        self.config = config
        self.model_rules = config['model_rules']
        self.looker_config = config['looker']
        self.connection_name = self.looker_config['connection']

        # Initialize the modular generators
        self.view_generator = LookMLViewGenerator(config)
        self.measure_generator = LookMLMeasureGenerator(config)
        self.explore_generator = LookMLExploreGenerator(config)

    def generate_view_dict_for_table_metadata(self, table_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate LookML view dictionary for a single table using metadata.

        Args:
            table_metadata: Table metadata dictionary from MetadataExtractor

        Returns:
            Dictionary containing the LookML view definition
        """
        # Generate the base view dictionary
        view_dict = self.view_generator.generate_view_dict(table_metadata)

        # Generate measures and add them to the view
        measures = self.measure_generator.generate_measures_for_view(
            table_metadata)
        if measures:
            view_name = list(view_dict['view'].keys())[0]
            if 'measure' not in view_dict['view'][view_name]:
                view_dict['view'][view_name]['measure'] = []

            # Convert measure list to the correct format
            for measure in measures:
                for measure_name, measure_def in measure.items():
                    view_dict['view'][view_name]['measure'].append(
                        {measure_name: measure_def})

        return view_dict

    def generate_view_for_table(self, table_metadata: Dict[str, Any]) -> str:
        """
        Generate LookML view content for a single table (backward compatibility).

        Args:
            table_metadata: Table metadata dictionary

        Returns:
            String containing the LookML view definition
        """
        view_dict = self.generate_view_dict_for_table_metadata(table_metadata)
        return lkml.dump(view_dict)

    def generate_explores_dict(self, tables_metadata: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate LookML explores dictionary for multiple tables.

        Args:
            tables_metadata: Dictionary of table metadata

        Returns:
            Dictionary containing the LookML explores definition
        """
        explores = self.explore_generator.generate_explores_for_views(
            tables_metadata)

        # Combine all explores into a single dictionary
        combined_explores = {}
        for explore in explores:
            if 'explore' in explore:
                combined_explores.update(explore['explore'])

        return {'explore': combined_explores} if combined_explores else {}

    def generate_complete_lookml_project(self, tables_metadata: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a complete LookML project with views and explores.

        Args:
            tables_metadata: Dictionary of table metadata

        Returns:
            Dictionary containing the complete LookML project
        """
        project_dict = {}

        # Generate all views
        views = {}
        for table_key, table_metadata in tables_metadata.items():
            view_dict = self.generate_view_dict_for_table_metadata(
                table_metadata)
            if 'view' in view_dict:
                views.update(view_dict['view'])

        if views:
            project_dict['view'] = views

        # Generate explores
        explores_dict = self.generate_explores_dict(tables_metadata)
        if explores_dict and 'explore' in explores_dict:
            project_dict.update(explores_dict)

        return project_dict


class LookMLFileWriter:
    """
    Handles writing LookML files using the lkml library for proper serialization.
    Following the droughty pattern of treating LookML as data structures.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the file writer.

        Args:
            config: The loaded configuration dictionary
        """
        self.config = config
        self.looker_config = config['looker']

    def write_views_file(self, view_contents: List[str]) -> str:
        """
        Write a single LookML file containing all generated views (backward compatibility).

        Args:
            view_contents: List of generated LookML view content strings

        Returns:
            Path to the written file
        """
        project_path = Path(self.looker_config['project_path'])
        views_path = self.looker_config['views_path']

        # views_path is the exact file path relative to project_path
        file_path = project_path / views_path

        # Create the directory structure if it doesn't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Combine all view contents into a single file
        combined_content = "\n\n".join(view_contents)

        # Write the file
        with open(file_path, 'w') as f:
            f.write(combined_content)

        return str(file_path)

    def write_lookml_dict_file(self, lookml_dict: Dict[str, Any], file_suffix: str = "views") -> str:
        """
        Write a LookML file from a dictionary using the lkml library.

        Args:
            lookml_dict: Dictionary containing LookML structure
            file_suffix: Suffix for the file name (e.g., "views", "explores")

        Returns:
            Path to the written file
        """
        project_path = Path(self.looker_config['project_path'])

        # Generate file name
        if file_suffix == "views":
            file_path = project_path / self.looker_config['views_path']
        elif file_suffix == "explores":
            file_path = project_path / self.looker_config['explores_path']
        else:
            # For any other file types, generate a new file name using views_path as base
            base_name = Path(self.looker_config['views_path']).stem
            base_dir = Path(self.looker_config['views_path']).parent
            file_path = project_path / base_dir / \
                f"{base_name}_{file_suffix}.view.lkml"

        # Create the directory structure if it doesn't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Use lkml library to dump the dictionary to LookML format
        lookml_content = lkml.dump(lookml_dict)

        # Write the file
        with open(file_path, 'w') as f:
            f.write(lookml_content)

        return str(file_path)

    def write_views_dict_file(self, views_dict: Dict[str, Any]) -> str:
        """
        Write views from dictionary to file.

        Args:
            views_dict: Dictionary containing view definitions

        Returns:
            Path to the written file
        """
        return self.write_lookml_dict_file(views_dict, "views")

    def write_explores_dict_file(self, explores_dict: Dict[str, Any]) -> str:
        """
        Write explores from dictionary to file.

        Args:
            explores_dict: Dictionary containing explore definitions

        Returns:
            Path to the written file
        """
        return self.write_lookml_dict_file(explores_dict, "explores")

    def write_complete_project(self, project_dict: Dict[str, Any]) -> List[str]:
        """
        Write a complete LookML project with separate files for views and explores.

        Args:
            project_dict: Dictionary containing the complete project structure

        Returns:
            List of paths to the written files
        """
        written_files = []

        # Write views file
        if 'view' in project_dict:
            views_file = self.write_lookml_dict_file(
                {'view': project_dict['view']}, "views")
            written_files.append(views_file)

        # Write explores file
        if 'explore' in project_dict:
            explores_file = self.write_lookml_dict_file(
                {'explore': project_dict['explore']}, "explores")
            written_files.append(explores_file)

        return written_files
