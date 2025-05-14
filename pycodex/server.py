"""
MCP server implementation for PyCodex using FastMCP.
"""

import pathlib
from typing import Dict, List, Optional, Any

from fastmcp import FastMCP
from rich.console import Console
from sqlalchemy import select, func

from pycodex.core.scanner import PyScanner
from pycodex.core.parser import PyParser
from pycodex.core.indexer import PyIndexer
from pycodex.core.search import PySearch
from pycodex.models.database import Module, Project

class PyCodexServer:
    """PyCodex MCP server implementation."""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the PyCodex server.

        Args:
            db_path: Path to the SQLite database file
        """
        self.console = Console()
        self.indexer = PyIndexer(db_path)
        self.searcher = PySearch(db_path)

        # Initialize the MCP server
        self.mcp: FastMCP = FastMCP("PyCodex")

        # Register tools and resources
        self._register_tools()
        self._register_resources()

    def _register_tools(self) -> None:
        """Register tools with the MCP server."""

        @self.mcp.tool()
        def index_directory(directory: str, project_name: Optional[str] = None) -> Dict[str, Any]:
            """
            Index Python files in a directory.

            Args:
                directory: Path to the directory to index
                project_name: Optional name for the project (defaults to directory name)

            Returns:
                Dictionary with project_id and file_count
            """
            dir_path = pathlib.Path(directory).resolve()
            if not dir_path.exists() or not dir_path.is_dir():
                return {"error": f"Directory not found: {directory}"}

            # Use directory name as project name if not provided
            if project_name is None:
                project_name = dir_path.name

            try:
                # Scan for Python files
                scanner = PyScanner(str(dir_path), console=self.console)
                files = scanner.scan_to_list()

                if not files:
                    return {"project_id": None, "file_count": 0, "message": "No Python files found"}

                # Parse files
                modules = []
                errors = []

                for file_path in files:
                    try:
                        module_info = PyParser.parse_file(file_path)
                        modules.append(module_info)
                    except Exception as e:
                        errors.append(f"Error parsing {file_path}: {e}")

                # Index modules
                project_id = self.indexer.index_project(project_name, str(dir_path), modules)

                return {
                    "project_id": project_id,
                    "file_count": len(modules),
                    "errors": errors,
                    "message": f"Indexed {len(modules)} files",
                }

            except FileNotFoundError as e:
                return {"error": str(e)}
            except Exception as e:
                return {"error": f"Error indexing directory: {e}"}

        @self.mcp.tool()
        def search_code(query: str, project_id: Optional[int] = None) -> Dict[str, Any]:
            """
            Search for code in indexed projects.

            Args:
                query: Search query
                project_id: Optional project ID to restrict search

            Returns:
                Dictionary with search results
            """
            try:
                results = self.searcher.search_code(query, project_id)

                # Format results for better display
                formatted_results = {"query": query, "results": self._format_search_results(results)}

                return formatted_results

            except Exception as e:
                return {"error": f"Error searching code: {e}"}

        @self.mcp.tool()
        def get_file_content(path: str) -> Dict[str, Any]:
            """
            Get the content of a file.

            Args:
                path: Path to the file

            Returns:
                Dictionary with file content and information
            """
            try:
                result = self.searcher.get_file_content(path)
                if not result:
                    return {"error": f"File not found or not indexed: {path}"}

                content, elements = result

                return {"path": path, "content": content, "elements": elements}

            except Exception as e:
                return {"error": f"Error getting file content: {e}"}

    def _register_resources(self) -> None:
        """Register resources with the MCP server."""

        @self.mcp.resource("pycodex://projects")
        def get_projects() -> Dict[str, Any]:
            """
            Get all indexed projects.

            Returns:
                Dictionary with project information
            """
            try:
                projects = self.searcher.get_projects()
                return {"projects": projects}
            except Exception as e:
                return {"error": f"Error getting projects: {e}"}

        @self.mcp.resource("pycodex://project/{project_id}")
        def get_project(project_id: int) -> Dict[str, Any]:
            """
            Get information about a specific project.

            Args:
                project_id: ID of the project

            Returns:
                Project information
            """
            try:
                session = self.indexer.Session()
                try:
                    # Get project
                    project_stmt = select(Project).filter_by(id=project_id)
                    project = session.scalar(project_stmt)
                    if not project:
                        return {"error": f"Project not found: {project_id}"}

                    # Count files
                    file_count_stmt = select(func.count()).select_from(Module).filter_by(project_id=project_id)
                    file_count = session.scalar(file_count_stmt)

                    return {
                        "id": project.id,
                        "name": project.name,
                        "root_path": project.root_path,
                        "file_count": file_count,
                        "created_at": project.created_at.isoformat(),
                        "updated_at": project.updated_at.isoformat(),
                    }
                finally:
                    session.close()
            except Exception as e:
                return {"error": f"Error getting project: {e}"}

    def _format_search_results(self, results: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Format search results for display."""
        formatted = []

        # Process modules
        for module in results.get("modules", []):
            formatted.append(
                {
                    "type": "module",
                    "name": module["name"],
                    "path": module["path"],
                    "description": module["docstring"] or f"Module {module['name']}",
                }
            )

        # Process classes
        for class_ in results.get("classes", []):
            formatted.append(
                {
                    "type": "class",
                    "name": class_["name"],
                    "path": class_["path"],
                    "location": {"line": class_["lineno"]},
                    "description": class_["docstring"]
                    or f"Class {class_['name']} in {class_['module_name']}",
                }
            )

        # Process functions
        for function in results.get("functions", []):
            # Format the name based on whether it's a method or a function
            if function.get("class_name"):
                name = f"{function['class_name']}.{function['name']}"
                type_ = "method"
            else:
                name = function["name"]
                type_ = "function"

            formatted.append(
                {
                    "type": type_,
                    "name": name,
                    "path": function["path"],
                    "location": {"line": function["lineno"]},
                    "description": function["docstring"]
                    or f"{type_.capitalize()} {name} in {function['module_name']}",
                }
            )

        # Process variables
        for variable in results.get("variables", []):
            formatted.append(
                {
                    "type": "variable",
                    "name": variable["name"],
                    "path": variable["path"],
                    "location": {"line": variable["lineno"]},
                    "description": f"Variable {variable['name']} = {variable['value']}",
                }
            )

        return formatted

    def run(self) -> None:
        """Run the MCP server."""
        self.mcp.run()


def create_server(db_path: Optional[str] = None) -> PyCodexServer:
    """
    Create and return a new PyCodex server instance.

    Args:
        db_path: Path to the SQLite database file

    Returns:
        PyCodex server instance
    """
    return PyCodexServer(db_path)
