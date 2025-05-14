"""
Indexer module for storing parsed Python code in a database.
"""

import datetime
import json
from typing import List, Optional

from sqlalchemy.orm import Session, sessionmaker

from pycodex.models.database import (
    Project,
    Module,
    Function,
    Class,
    Import,
    Variable,
    init_database,
)
from pycodex.core.parser import ModuleInfo, FunctionInfo, ClassInfo, ImportInfo


class PyIndexer:
    """Indexer for storing parsed Python code in a database."""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the indexer.

        Args:
            db_path: Path to the SQLite database file
        """
        self.engine = init_database(db_path)
        self.Session = sessionmaker(bind=self.engine)

    def index_project(self, name: str, root_path: str, modules: List[ModuleInfo]) -> int:
        """
        Index a project and its modules.

        Args:
            name: Project name
            root_path: Root path of the project
            modules: List of ModuleInfo objects to index

        Returns:
            Project ID
        """
        session = self.Session()

        try:
            # Check if project already exists
            project = session.query(Project).filter_by(root_path=root_path).first()

            if not project:
                # Create new project
                project = Project(name=name, root_path=root_path)
                session.add(project)
                session.flush()

            # Index each module
            for module_info in modules:
                self._index_module(session, project.id, module_info)

            session.commit()
            return project.id

        except Exception as e:
            session.rollback()
            raise e

        finally:
            session.close()

    def _index_module(self, session: Session, project_id: int, module_info: ModuleInfo) -> Module:
        """Index a single module."""
        # Check if module already exists
        module = session.query(Module).filter_by(project_id=project_id, path=str(module_info.path)).first()

        if module:
            # Clear existing data
            session.query(Function).filter_by(module_id=module.id, class_id=None).delete()
            session.query(Class).filter_by(module_id=module.id).delete()
            session.query(Import).filter_by(module_id=module.id).delete()
            session.query(Variable).filter_by(module_id=module.id).delete()
        else:
            # Create new module
            module = Module(
                project_id=project_id,
                name=module_info.module_name,
                path=str(module_info.path),
                docstring=module_info.docstring,
            )
            session.add(module)
            session.flush()

        # Index imports
        for import_info in module_info.imports:
            self._index_import(session, module.id, import_info)

        # Index variables
        for name, (lineno, value) in module_info.variables.items():
            self._index_variable(session, module.id, name, lineno, value)

        # Index classes
        for class_info in module_info.classes:
            self._index_class(session, module.id, class_info)

        # Index functions (only top-level functions, class methods are indexed with their class)
        for func_info in module_info.functions:
            self._index_function(session, module.id, None, func_info)

        module.last_indexed = datetime.datetime.utcnow()
        return module

    def _index_import(self, session: Session, module_id: int, import_info: ImportInfo) -> Import:
        """Index a single import."""
        import_db = Import(
            module_id=module_id,
            module_name=import_info.module_name,
            alias=import_info.alias,
            is_from_import=import_info.is_from_import,
            parent_module=import_info.parent_module,
        )
        session.add(import_db)
        return import_db

    def _index_function(
        self, session: Session, module_id: int, class_id: Optional[int], func_info: FunctionInfo
    ) -> Function:
        """Index a single function."""
        function = Function(
            module_id=module_id,
            class_id=class_id,
            name=func_info.name,
            docstring=func_info.docstring,
            lineno=func_info.lineno,
            end_lineno=func_info.end_lineno,
            args=json.dumps(func_info.args),
            decorators=json.dumps(func_info.decorators),
            return_annotation=func_info.return_annotation,
        )
        session.add(function)
        return function

    def _index_class(self, session: Session, module_id: int, class_info: ClassInfo) -> Class:
        """Index a single class."""
        class_db = Class(
            module_id=module_id,
            name=class_info.name,
            docstring=class_info.docstring,
            lineno=class_info.lineno,
            end_lineno=class_info.end_lineno,
            base_classes=json.dumps(class_info.base_classes),
            decorators=json.dumps(class_info.decorators),
        )
        session.add(class_db)
        session.flush()

        # Index methods
        for method_info in class_info.methods:
            self._index_function(session, module_id, class_db.id, method_info)

        return class_db

    def _index_variable(
        self, session: Session, module_id: int, name: str, lineno: int, value: str
    ) -> Variable:
        """Index a single variable."""
        variable = Variable(module_id=module_id, name=name, lineno=lineno, value=value)
        session.add(variable)
        return variable
