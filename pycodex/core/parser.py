"""
Parser module for extracting information from Python files.
"""

import ast
import pathlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from astroid import parse as astroid_parse  # type: ignore
from astroid import nodes


@dataclass
class ImportInfo:
    """Information about imports in a Python file."""

    module_name: str
    alias: Optional[str] = None
    is_from_import: bool = False
    parent_module: Optional[str] = None


@dataclass
class FunctionInfo:
    """Information about a function in a Python file."""

    name: str
    docstring: Optional[str]
    lineno: int
    end_lineno: int
    args: List[str]
    decorators: List[str]
    return_annotation: Optional[str]


@dataclass
class ClassInfo:
    """Information about a class in a Python file."""

    name: str
    docstring: Optional[str]
    lineno: int
    end_lineno: int
    methods: List[FunctionInfo] = field(default_factory=list)
    base_classes: List[str] = field(default_factory=list)
    decorators: List[str] = field(default_factory=list)


@dataclass
class ModuleInfo:
    """Information about a Python module."""

    path: pathlib.Path
    docstring: Optional[str]
    imports: List[ImportInfo] = field(default_factory=list)
    functions: List[FunctionInfo] = field(default_factory=list)
    classes: List[ClassInfo] = field(default_factory=list)
    variables: Dict[str, Tuple[int, str]] = field(default_factory=dict)

    @property
    def module_name(self) -> str:
        """Get the module name from the path."""
        return self.path.stem


class PyParser:
    """Parser for extracting information from Python files."""

    @staticmethod
    def parse_file(file_path: pathlib.Path) -> ModuleInfo:
        """
        Parse a Python file and extract information.

        Args:
            file_path: Path to the Python file

        Returns:
            ModuleInfo object containing file information
        """
        try:
            # Parse with astroid for more comprehensive info
            module = astroid_parse(file_path.read_text(), path=str(file_path))

            # Get module docstring
            docstring = module.doc or None

            # Parse imports
            imports = PyParser._parse_imports(module)

            # Parse functions
            functions = PyParser._parse_functions(module)

            # Parse classes
            classes = PyParser._parse_classes(module)

            # Parse variables
            variables = PyParser._parse_variables(module)

            return ModuleInfo(
                path=file_path,
                docstring=docstring,
                imports=imports,
                functions=functions,
                classes=classes,
                variables=variables,
            )
        except Exception as e:
            # Fallback to basic parsing if astroid fails
            print(f"Error parsing {file_path}: {e}")
            return PyParser._basic_parse(file_path)

    @staticmethod
    def _parse_imports(module: nodes.Module) -> List[ImportInfo]:
        """Parse imports from a module."""
        imports = []

        # Process import statements
        for node in module.body:
            if isinstance(node, nodes.Import):
                for name, alias in node.names:
                    imports.append(ImportInfo(module_name=name, alias=alias, is_from_import=False))
            elif isinstance(node, nodes.ImportFrom):
                for name, alias in node.names:
                    imports.append(
                        ImportInfo(
                            module_name=name, alias=alias, is_from_import=True, parent_module=node.modname
                        )
                    )

        return imports

    @staticmethod
    def _parse_functions(module: nodes.Module) -> List[FunctionInfo]:
        """Parse functions from a module."""
        functions = []

        for node in module.body:
            if isinstance(node, nodes.FunctionDef):
                functions.append(PyParser._function_to_info(node))

        return functions

    @staticmethod
    def _function_to_info(node: nodes.FunctionDef) -> FunctionInfo:
        """Convert a function node to FunctionInfo."""
        # Get arguments
        args = [arg.name for arg in node.args.args]

        # Get decorators
        decorators = [d.as_string() for d in node.decorators.nodes] if node.decorators else []

        # Get return annotation
        returns = node.returns.as_string() if node.returns else None

        return FunctionInfo(
            name=node.name,
            docstring=node.doc or None,
            lineno=node.lineno,
            end_lineno=node.end_lineno or node.lineno,
            args=args,
            decorators=decorators,
            return_annotation=returns,
        )

    @staticmethod
    def _parse_classes(module: nodes.Module) -> List[ClassInfo]:
        """Parse classes from a module."""
        classes = []

        for node in module.body:
            if isinstance(node, nodes.ClassDef):
                # Get methods
                methods = []
                for child in node.body:
                    if isinstance(child, nodes.FunctionDef):
                        methods.append(PyParser._function_to_info(child))

                # Get base classes
                bases = [base.as_string() for base in node.bases]

                # Get decorators
                decorators = [d.as_string() for d in node.decorators.nodes] if node.decorators else []

                classes.append(
                    ClassInfo(
                        name=node.name,
                        docstring=node.doc or None,
                        lineno=node.lineno,
                        end_lineno=node.end_lineno or node.lineno,
                        methods=methods,
                        base_classes=bases,
                        decorators=decorators,
                    )
                )

        return classes

    @staticmethod
    def _parse_variables(module: nodes.Module) -> Dict[str, Tuple[int, str]]:
        """Parse variables from a module."""
        variables: Dict[str, Tuple[int, str]] = {}

        for node in module.body:
            if isinstance(node, nodes.Assign):
                # Handle basic assignments
                for target in node.targets:
                    if isinstance(target, nodes.AssignName):
                        value = (
                            node.value.as_string() if hasattr(node.value, "as_string") else str(node.value)
                        )
                        variables[target.name] = (node.lineno, value)
            elif isinstance(node, nodes.AnnAssign):
                # Handle annotated assignments
                if isinstance(node.target, nodes.Name):
                    annotation = (
                        node.annotation.as_string()
                        if hasattr(node.annotation, "as_string")
                        else str(node.annotation)
                    )
                    variables[node.target.name] = (node.lineno, annotation)

        return variables

    @staticmethod
    def _basic_parse(file_path: pathlib.Path) -> ModuleInfo:
        """Basic parsing fallback using the stdlib ast module."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=str(file_path))

            # Extract a basic docstring if present
            docstring = ast.get_docstring(tree) or None

            return ModuleInfo(
                path=file_path, docstring=docstring, imports=[], functions=[], classes=[], variables={}
            )
        except Exception as e:
            print(f"Basic parsing failed for {file_path}: {e}")
            # Return an empty ModuleInfo if all parsing fails
            return ModuleInfo(
                path=file_path, docstring=None, imports=[], functions=[], classes=[], variables={}
            )
