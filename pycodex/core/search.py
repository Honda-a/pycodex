"""
Search module for querying the indexed code.
"""

import re
from typing import Dict, List, Optional, Tuple, Any, cast

from sqlalchemy import select, or_, func
from sqlalchemy.orm import sessionmaker
from pycodex.models.database import Project, Module, Class, Function, Variable, Import, create_db_engine


class PySearch:
    """Search class for querying the indexed code."""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the search.

        Args:
            db_path: Path to the SQLite database file
        """
        self.engine = create_db_engine(db_path)
        self.Session = sessionmaker(bind=self.engine)

    def search_code(
        self, query: str, project_id: Optional[int] = None, limit: int = 20
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search the indexed code.

        Args:
            query: Search query
            project_id: Optional project ID to restrict search
            limit: Maximum number of results per category

        Returns:
            Dictionary with search results
        """
        # Check for special search syntax
        if ":" in query:
            return self._structured_search(query, project_id, limit)
        else:
            return self._free_text_search(query, project_id, limit)

    def _free_text_search(
        self, query: str, project_id: Optional[int] = None, limit: int = 20
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Perform a free text search across all fields."""
        session = self.Session()

        try:
            results: Dict[str, List[Dict[str, Any]]] = {
                "modules": [],
                "classes": [],
                "functions": [],
                "variables": [],
            }

            # Convert query to lowercase for case-insensitive search
            query_lower = f"%{query.lower()}%"

            # Base filters
            base_filters = []
            if project_id is not None:
                base_filters.append(Module.project_id == project_id)

            # Search modules
            module_stmt = (
                select(Module)
                .filter(
                    or_(
                        func.lower(Module.name).like(query_lower),
                        (
                            func.lower(Module.docstring).like(query_lower)
                            if Module.docstring is not None
                            else False
                        ),
                    ),
                    *base_filters,
                )
                .limit(limit)
            )

            for module in session.scalars(module_stmt):
                results["modules"].append(
                    {
                        "id": module.id,
                        "name": module.name,
                        "path": module.path,
                        "docstring": self._truncate_text(module.docstring),
                    }
                )

            # Search classes
            query_conditions = (
                func.lower(Class.name).like(query_lower)
                if Class.docstring is None
                else or_(
                    func.lower(Class.name).like(query_lower),
                    func.lower(Class.docstring).like(query_lower),
                )
            )
            class_stmt = (
                select(Class)
                .join(Module)
                .filter(
                    query_conditions,
                    *base_filters,
                )
                .limit(limit)
            )

            for class_obj in session.scalars(class_stmt):
                results["classes"].append(
                    {
                        "id": class_obj.id,
                        "name": class_obj.name,
                        "module_name": class_obj.module.name,
                        "path": class_obj.module.path,
                        "lineno": class_obj.lineno,
                        "docstring": self._truncate_text(class_obj.docstring),
                    }
                )

            # Search functions
            function_stmt = (
                select(Function)
                .join(Module)
                .filter(
                    or_(
                        func.lower(Function.name).like(query_lower),
                        (
                            func.lower(Function.docstring).like(query_lower)
                            if Function.docstring is not None
                            else False
                        ),
                    ),
                    *base_filters,
                )
                .limit(limit)
            )

            for function in session.scalars(function_stmt):
                class_name: Optional[str] = None
                if function.class_id:
                    class_stmt = select(Class).filter_by(id=function.class_id)
                    parent_class: Optional[Class] = session.scalar(class_stmt)
                    if parent_class is not None:
                        class_name = parent_class.name

                results["functions"].append(
                    {
                        "id": function.id,
                        "name": function.name,
                        "module_name": function.module.name,
                        "class_name": class_name,
                        "path": function.module.path,
                        "lineno": function.lineno,
                        "docstring": self._truncate_text(function.docstring),
                    }
                )

            # Search variables
            variable_stmt = (
                select(Variable)
                .join(Module)
                .filter(func.lower(Variable.name).like(query_lower), *base_filters)
                .limit(limit)
            )

            for variable in session.scalars(variable_stmt):
                results["variables"].append(
                    {
                        "id": variable.id,
                        "name": variable.name,
                        "module_name": variable.module.name,
                        "path": variable.module.path,
                        "lineno": variable.lineno,
                        "value": self._truncate_text(variable.value, max_length=100),
                    }
                )

            return results

        finally:
            session.close()

    def _structured_search(
        self, query: str, project_id: Optional[int] = None, limit: int = 20
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Parse and execute a structured search query."""
        # Parse query
        match = re.match(r"(\w+):(.+)", query)
        if not match:
            return self._free_text_search(query, project_id, limit)

        search_type, search_term = match.groups()
        search_term = search_term.strip()
        search_term_lower = f"%{search_term.lower()}%"

        session = self.Session()

        try:
            results: Dict[str, List[Dict[str, Any]]] = {
                "modules": [],
                "classes": [],
                "functions": [],
                "variables": [],
            }

            # Base filters
            base_filters = []
            if project_id is not None:
                base_filters.append(Module.project_id == project_id)

            if search_type == "module":
                # Search modules
                module_stmt = (
                    select(Module)
                    .filter(func.lower(Module.name).like(search_term_lower), *base_filters)
                    .limit(limit)
                )

                for module in session.scalars(module_stmt):
                    results["modules"].append(
                        {
                            "id": module.id,
                            "name": module.name,
                            "path": module.path,
                            "docstring": self._truncate_text(module.docstring),
                        }
                    )

            elif search_type == "class":
                # Search classes
                class_stmt = (
                    select(Class)
                    .join(Module)
                    .filter(func.lower(Class.name).like(search_term_lower), *base_filters)
                    .limit(limit)
                )

                for class_obj in session.scalars(class_stmt):
                    results["classes"].append(
                        {
                            "id": class_obj.id,
                            "name": class_obj.name,
                            "module_name": class_obj.module.name,
                            "path": class_obj.module.path,
                            "lineno": class_obj.lineno,
                            "docstring": self._truncate_text(class_obj.docstring),
                        }
                    )

            elif search_type == "function" or search_type == "method":
                # Search functions
                function_stmt = (
                    select(Function)
                    .join(Module)
                    .filter(func.lower(Function.name).like(search_term_lower), *base_filters)
                    .limit(limit)
                )

                for function in session.scalars(function_stmt):
                    class_name = None
                    if function.class_id:
                        class_stmt = select(Class).filter_by(id=function.class_id)
                        parent_class_obj: Optional[Class] = session.scalar(class_stmt)
                        if parent_class_obj is not None:
                            class_name = parent_class_obj.name

                    results["functions"].append(
                        {
                            "id": function.id,
                            "name": function.name,
                            "module_name": function.module.name,
                            "class_name": class_name,
                            "path": function.module.path,
                            "lineno": function.lineno,
                            "docstring": self._truncate_text(function.docstring),
                        }
                    )

            elif search_type == "var" or search_type == "variable":
                # Search variables
                variable_stmt = (
                    select(Variable)
                    .join(Module)
                    .filter(func.lower(Variable.name).like(search_term_lower), *base_filters)
                    .limit(limit)
                )

                for variable in session.scalars(variable_stmt):
                    results["variables"].append(
                        {
                            "id": variable.id,
                            "name": variable.name,
                            "module_name": variable.module.name,
                            "path": variable.module.path,
                            "lineno": variable.lineno,
                            "value": self._truncate_text(variable.value, max_length=100),
                        }
                    )

            elif search_type == "import":
                # Search imports
                import_stmt = (
                    select(Import)
                    .join(Module)
                    .filter(
                        or_(
                            func.lower(Import.module_name).like(search_term_lower),
                            (
                                func.lower(Import.parent_module).like(search_term_lower)
                                if Import.parent_module is not None
                                else False
                            ),
                        ),
                        *base_filters,
                    )
                    .limit(limit)
                )

                for import_ in session.scalars(import_stmt):
                    if import_.is_from_import:
                        name = f"from {import_.parent_module} import {import_.module_name}"
                        if import_.alias:
                            name += f" as {import_.alias}"
                    else:
                        name = f"import {import_.module_name}"
                        if import_.alias:
                            name += f" as {import_.alias}"

                    # Add to modules for now
                    results["modules"].append(
                        {
                            "id": import_.module_id,
                            "name": name,
                            "path": import_.module.path,
                            "docstring": f"Import in {import_.module.name}",
                        }
                    )

            elif search_type == "doc" or search_type == "docstring":
                # Search docstrings across all types

                # Search module docstrings
                module_stmt = (
                    select(Module)
                    .filter(
                        (
                            func.lower(Module.docstring).like(search_term_lower)
                            if Module.docstring is not None
                            else False
                        ),
                        *base_filters,
                    )
                    .limit(limit)
                )

                for module in session.scalars(module_stmt):
                    results["modules"].append(
                        {
                            "id": module.id,
                            "name": module.name,
                            "path": module.path,
                            "docstring": self._truncate_text(module.docstring),
                        }
                    )

                # Search class docstrings
                class_stmt = (
                    select(Class)
                    .join(Module)
                    .filter(
                        (
                            func.lower(Class.docstring).like(search_term_lower)
                            if Class.docstring is not None
                            else False
                        ),
                        *base_filters,
                    )
                    .limit(limit)
                )

                for class_obj in session.scalars(class_stmt):
                    results["classes"].append(
                        {
                            "id": class_obj.id,
                            "name": class_obj.name,
                            "module_name": class_obj.module.name,
                            "path": class_obj.module.path,
                            "lineno": class_obj.lineno,
                            "docstring": self._truncate_text(class_obj.docstring),
                        }
                    )

                # Search function docstrings
                function_stmt = (
                    select(Function)
                    .join(Module)
                    .filter(
                        (
                            func.lower(Function.docstring).like(search_term_lower)
                            if Function.docstring is not None
                            else False
                        ),
                        *base_filters,
                    )
                    .limit(limit)
                )

                for function in session.scalars(function_stmt):
                    class_name = None
                    if function.class_id:
                        class_stmt = select(Class).filter_by(id=function.class_id)
                        parent_class_doc: Optional[Class] = session.scalar(class_stmt)
                        if parent_class_doc is not None:
                            class_name = parent_class_doc.name

                    results["functions"].append(
                        {
                            "id": function.id,
                            "name": function.name,
                            "module_name": function.module.name,
                            "class_name": class_name,
                            "path": function.module.path,
                            "lineno": function.lineno,
                            "docstring": self._truncate_text(function.docstring),
                        }
                    )

            else:
                # Unknown search type, fall back to free text search
                return self._free_text_search(search_term, project_id, limit)

            return results

        finally:
            session.close()

    def get_file_content(self, path: str) -> Optional[Tuple[str, List[Dict[str, Any]]]]:
        """
        Get the content of a file and its indexed elements.

        Args:
            path: Path to the file

        Returns:
            Tuple containing the file content and its indexed elements or None if not found
        """
        session = self.Session()

        try:
            # Find the module
            module_stmt = select(Module).filter_by(path=path)
            module = session.scalar(module_stmt)
            if not module:
                return None

            # Read the file content
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as e:
                print(f"Error reading file {path}: {e}")
                content = f"Error reading file: {e}"

            # Get all elements in the file
            elements = []

            # Functions
            function_stmt = select(Function).filter_by(module_id=module.id, class_id=None)
            for func in session.scalars(function_stmt):
                elements.append(
                    {
                        "type": "function",
                        "name": func.name,
                        "lineno": func.lineno,
                        "end_lineno": func.end_lineno,
                        "docstring": func.docstring,
                    }
                )

            # Classes
            class_stmt = select(Class).filter_by(module_id=module.id)
            for class_obj in session.scalars(class_stmt):
                elements.append(
                    {
                        "type": "class",
                        "name": class_obj.name,
                        "lineno": class_obj.lineno,
                        "end_lineno": class_obj.end_lineno,
                        "docstring": class_obj.docstring,
                    }
                )

                # Methods
                method_stmt = select(Function).filter_by(class_id=class_obj.id)
                for method in session.scalars(method_stmt):
                    elements.append(
                        {
                            "type": "method",
                            "name": f"{class_obj.name}.{method.name}",
                            "lineno": method.lineno,
                            "end_lineno": method.end_lineno,
                            "docstring": method.docstring,
                        }
                    )

            # Variables
            variable_stmt = select(Variable).filter_by(module_id=module.id)
            for var in session.scalars(variable_stmt):
                elements.append(
                    {"type": "variable", "name": var.name, "lineno": var.lineno, "value": var.value}
                )

            # Sort elements by line number
            elements.sort(key=lambda x: cast(int, x["lineno"]))

            return (content, elements)

        finally:
            session.close()

    def get_projects(self) -> List[Dict[str, Any]]:
        """
        Get all indexed projects.

        Returns:
            List of project dictionaries
        """
        session = self.Session()

        try:
            projects = []
            project_stmt = select(Project)

            for project in session.scalars(project_stmt):
                # Count files
                file_count = session.scalar(
                    select(func.count()).select_from(Module).filter_by(project_id=project.id)
                )

                projects.append(
                    {
                        "id": project.id,
                        "name": project.name,
                        "root_path": project.root_path,
                        "file_count": file_count,
                        "created_at": project.created_at.isoformat(),
                        "updated_at": project.updated_at.isoformat(),
                    }
                )

            return projects

        finally:
            session.close()

    @staticmethod
    def _truncate_text(text: Optional[str], max_length: int = 200) -> Optional[str]:
        """Truncate text to maximum length."""
        if not text:
            return None

        if len(text) <= max_length:
            return text

        return text[:max_length] + "..."
