"""
Scanner module for finding Python files while respecting gitignore patterns.
"""

import pathlib
from typing import Iterator, List, Optional

import gitignore_parser
from rich.console import Console


class PyScanner:
    """Scanner for Python files that respects gitignore patterns."""

    def __init__(
        self, root_dir: str, gitignore_path: Optional[str] = None, console: Optional[Console] = None
    ):
        """
        Initialize the scanner.

        Args:
            root_dir: The root directory to scan
            gitignore_path: Path to the gitignore file. If None, will look for .gitignore in root_dir
            console: Rich console for output. If None, a new console will be created.
        """
        self.console = console or Console()
        self.root_dir = pathlib.Path(root_dir).resolve()

        # Find and parse gitignore
        if gitignore_path:
            gitignore_file = pathlib.Path(gitignore_path)
        else:
            gitignore_file = self.root_dir / ".gitignore"

        if gitignore_file.exists():
            self.matches_gitignore = gitignore_parser.parse_gitignore(gitignore_file)
            self.console.log(f"Using gitignore from: {gitignore_file}")
        else:
            # If no gitignore exists, raise error as specified
            raise FileNotFoundError(f"No .gitignore file found in {self.root_dir}")

    def scan(self) -> Iterator[pathlib.Path]:
        """
        Scan for Python files in the root directory, respecting gitignore patterns.

        Returns:
            An iterator of Python file paths
        """
        self.console.log(f"Scanning for Python files in {self.root_dir}")
        files_count = 0
        ignored_count = 0

        for path in self.root_dir.glob("**/*.py"):
            # Skip files that match gitignore patterns
            if self.matches_gitignore(str(path)):
                ignored_count += 1
                continue
            files_count += 1
            yield path

        self.console.log(f"Found {files_count} Python files (ignored {ignored_count} files)")

    def scan_to_list(self) -> List[pathlib.Path]:
        """
        Scan for Python files and return as a list.

        Returns:
            A list of Python file paths
        """
        return list(self.scan())
