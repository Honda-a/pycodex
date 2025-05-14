"""
CLI module for PyCodex.
"""

import os
import pathlib
from typing import Annotated, Optional

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
import typer

from pycodex.core.scanner import PyScanner
from pycodex.core.parser import PyParser
from pycodex.core.indexer import PyIndexer
from pycodex.core.search import PySearch
from pycodex.server import create_server

# Create Typer app
app = typer.Typer(
    name="pycodex",
    help="Python code indexing and search for Claude Desktop",
    add_completion=False,
)

console = Console()


@app.command()
def index(
    directory: Optional[str] = typer.Argument(
        ..., help="Directory to index. If not provided, the current working directory will be used."
    ),
    project_name: Optional[str] = typer.Option(
        ..., "--name", "-n", help="Project name. If not provided, the directory name will be used."
    ),
    db_path: Optional[str] = typer.Option(..., "--db", "-d", help="Path to the SQLite database file."),
) -> None:
    """
    Index Python files in a directory.
    """
    # Use current working directory if not provided
    if directory is None:
        directory = os.getcwd()

    dir_path = pathlib.Path(directory).resolve()
    console.print(f"Indexing Python files in [bold cyan]{dir_path}[/]")

    # Use directory name as project name if not provided
    if project_name is None:
        project_name = dir_path.name

    try:
        # Scan for Python files
        scanner = PyScanner(str(dir_path), console=console)
        files = scanner.scan_to_list()

        if not files:
            console.print("[bold red]No Python files found[/]")
            return

        # Parse files
        console.print(f"Parsing {len(files)} Python files...")

        modules = []
        errors = []

        with console.status("Parsing files..."):
            for file_path in files:
                try:
                    module_info = PyParser.parse_file(file_path)
                    modules.append(module_info)
                except Exception as e:
                    errors.append(f"Error parsing {file_path}: {e}")

        # Index modules
        console.print(f"Indexing {len(modules)} modules...")

        indexer = PyIndexer(db_path)
        with console.status("Indexing modules..."):
            project_id = indexer.index_project(project_name, str(dir_path), modules)

        if errors:
            console.print(f"[bold yellow]Encountered {len(errors)} errors during parsing:[/]")
            for error in errors[:5]:  # Show first 5 errors
                console.print(f"  [yellow]{error}[/]")

            if len(errors) > 5:
                console.print(f"  [yellow]...and {len(errors) - 5} more[/]")

        console.print(
            f"\n[bold green]Successfully indexed {len(modules)} files with project ID {project_id}[/]"
        )

    except FileNotFoundError as e:
        console.print(f"[bold red]Error:[/] {e}")
    except Exception as e:
        console.print(f"[bold red]Error indexing directory:[/] {e}")


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    project_id: Optional[int] = typer.Option(..., "--project", "-p", help="Project ID to restrict search."),
    db_path: Optional[str] = typer.Option(..., "--db", "-d", help="Path to the SQLite database file."),
    limit: int = typer.Option(20, "--limit", "-l", help="Maximum number of results per category."),
) -> None:
    """
    Search for code in indexed projects.
    """
    console.print(f"Searching for: [bold cyan]{query}[/]")

    try:
        searcher = PySearch(db_path)
        results = searcher.search_code(query, project_id, limit)

        if not any(results.values()):
            console.print("[bold yellow]No results found[/]")
            return

        # Display results
        console.print("\n[bold green]Search Results:[/]\n")

        if results["modules"]:
            table = Table(title="Modules")
            table.add_column("Name", style="cyan")
            table.add_column("Path")
            table.add_column("Description")

            for module in results["modules"]:
                table.add_row(module["name"], module["path"], module["docstring"] or "")

            console.print(table)

        if results["classes"]:
            table = Table(title="Classes")
            table.add_column("Name", style="cyan")
            table.add_column("Module")
            table.add_column("Line")
            table.add_column("Description")

            for class_ in results["classes"]:
                table.add_row(
                    class_["name"], class_["module_name"], str(class_["lineno"]), class_["docstring"] or ""
                )

            console.print(table)

        if results["functions"]:
            table = Table(title="Functions and Methods")
            table.add_column("Name", style="cyan")
            table.add_column("Module")
            table.add_column("Class", style="magenta")
            table.add_column("Line")
            table.add_column("Description")

            for function in results["functions"]:
                table.add_row(
                    function["name"],
                    function["module_name"],
                    function.get("class_name", ""),
                    str(function["lineno"]),
                    function["docstring"] or "",
                )

            console.print(table)

        if results["variables"]:
            table = Table(title="Variables")
            table.add_column("Name", style="cyan")
            table.add_column("Module")
            table.add_column("Line")
            table.add_column("Value")

            for variable in results["variables"]:
                table.add_row(
                    variable["name"],
                    variable["module_name"],
                    str(variable["lineno"]),
                    variable["value"] or "",
                )

            console.print(table)

    except Exception as e:
        console.print(f"[bold red]Error searching code:[/] {e}")


@app.command()
def view(
    path: str = typer.Argument(..., help="Path to the file to view"),
    db_path: Optional[str] = typer.Option(..., "--db", "-d", help="Path to the SQLite database file."),
) -> None:
    """
    View a file's content with syntax highlighting.
    """
    try:
        file_path = pathlib.Path(path).resolve()

        searcher = PySearch(db_path)
        result = searcher.get_file_content(str(file_path))

        if not result:
            console.print(f"[bold red]File not found or not indexed: {path}[/]")
            return

        content, elements = result

        # Create a map of line numbers to elements for annotation
        line_map = {}
        for element in elements:
            line_map[element["lineno"]] = element

        # Display file content with syntax highlighting
        syntax = Syntax(content, "python", line_numbers=True, theme="monokai", word_wrap=True)

        console.print(Panel(syntax, title=f"File: {path}", expand=False))

        # Display element information
        if elements:
            console.print("\n[bold green]File Elements:[/]\n")

            table = Table()
            table.add_column("Type", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Line")
            table.add_column("Info")

            for element in elements:
                element_type = element["type"]
                name = element["name"]
                lineno = element["lineno"]

                if element_type in ("function", "method", "class"):
                    info = element.get("docstring", "")
                elif element_type == "variable":
                    info = element.get("value", "")
                else:
                    info = ""

                table.add_row(
                    element_type.capitalize(),
                    name,
                    str(lineno),
                    info[:50] + ("..." if info and len(info) > 50 else ""),
                )

            console.print(table)

    except Exception as e:
        console.print(f"[bold red]Error viewing file:[/] {e}")


@app.command()
def projects(
    db_path: Optional[str] = typer.Option(..., "--db", "-d", help="Path to the SQLite database file."),
) -> None:
    """
    List all indexed projects.
    """
    try:
        searcher = PySearch(db_path)
        projects = searcher.get_projects()

        if not projects:
            console.print("[bold yellow]No projects found[/]")
            return

        # Display projects
        console.print("\n[bold green]Indexed Projects:[/]\n")

        table = Table()
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Path")
        table.add_column("Files")
        table.add_column("Last Updated")

        for project in projects:
            table.add_row(
                str(project["id"]),
                project["name"],
                project["root_path"],
                str(project["file_count"]),
                project["updated_at"].split("T")[0],  # Just show the date
            )

        console.print(table)

    except Exception as e:
        console.print(f"[bold red]Error listing projects:[/] {e}")


@app.command()
def serve(
    db_path: Annotated[
        str,
        typer.Option(
            ..., "--db", "-d"
        ),
    ],
) -> None:
    """
    Run the MCP server for Claude Desktop integration.
    """
    console.print(
        Panel.fit(
            "[bold]PyCodex MCP Server[/]\n\n"
            "Running the Model Context Protocol server for Claude Desktop integration.\n"
            "To use with Claude Desktop, follow these steps:\n\n"
            "1. Add this server to your Claude Desktop configuration.\n"
            "2. Restart Claude Desktop or refresh the server list.\n"
            "3. Ask Claude to search your codebase.\n\n"
            "Press Ctrl+C to stop the server.",
            title="Server Starting",
            border_style="green",
        )
    )

    try:
        # Create and run the server
        server = create_server(db_path)
        server.run()
    except KeyboardInterrupt:
        console.print("\n[bold green]Server stopped[/]")
    except Exception as e:
        console.print(f"[bold red]Error running server:[/] {e}")


# @app.callback()
# def main() -> None:
#     """
#     PyCodex - Python code indexing and search for Claude Desktop
#     """
#     pass


if __name__ == "__main__":
    app()
