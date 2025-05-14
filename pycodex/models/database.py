"""
Database models for storing code information.
"""

import datetime
import pathlib
from typing import Optional, List
from datetime import UTC

from sqlalchemy import create_engine, String, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Project(Base):
    """Project model representing a code repository."""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    root_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(UTC)
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(UTC), onupdate=lambda: datetime.datetime.now(UTC)
    )

    modules: Mapped[List["Module"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Module(Base):
    """Module model representing a Python file."""

    __tablename__ = "modules"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(String(1024), nullable=False)
    docstring: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_indexed: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.now(UTC))

    project: Mapped["Project"] = relationship(back_populates="modules")
    functions: Mapped[List["Function"]] = relationship(back_populates="module", cascade="all, delete-orphan")
    classes: Mapped[List["Class"]] = relationship(back_populates="module", cascade="all, delete-orphan")
    imports: Mapped[List["Import"]] = relationship(back_populates="module", cascade="all, delete-orphan")
    variables: Mapped[List["Variable"]] = relationship(back_populates="module", cascade="all, delete-orphan")


class Function(Base):
    """Function model."""

    __tablename__ = "functions"

    id: Mapped[int] = mapped_column(primary_key=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id"), nullable=False)
    class_id: Mapped[Optional[int]] = mapped_column(ForeignKey("classes.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    docstring: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    lineno: Mapped[int] = mapped_column(nullable=False)
    end_lineno: Mapped[int] = mapped_column(nullable=False)
    args: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Stored as JSON
    decorators: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Stored as JSON
    return_annotation: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    module: Mapped["Module"] = relationship(back_populates="functions")
    class_: Mapped[Optional["Class"]] = relationship(back_populates="methods")


class Class(Base):
    """Class model."""

    __tablename__ = "classes"

    id: Mapped[int] = mapped_column(primary_key=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    docstring: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    lineno: Mapped[int] = mapped_column(nullable=False)
    end_lineno: Mapped[int] = mapped_column(nullable=False)
    base_classes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Stored as JSON
    decorators: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Stored as JSON

    module: Mapped["Module"] = relationship(back_populates="classes")
    methods: Mapped[List["Function"]] = relationship(back_populates="class_")


class Import(Base):
    """Import model."""

    __tablename__ = "imports"

    id: Mapped[int] = mapped_column(primary_key=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id"), nullable=False)
    module_name: Mapped[str] = mapped_column(String(255), nullable=False)
    alias: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_from_import: Mapped[bool] = mapped_column(Boolean, default=False)
    parent_module: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    module: Mapped["Module"] = relationship(back_populates="imports")


class Variable(Base):
    """Variable model."""

    __tablename__ = "variables"

    id: Mapped[int] = mapped_column(primary_key=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    lineno: Mapped[int] = mapped_column(nullable=False)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    module: Mapped["Module"] = relationship(back_populates="variables")


def get_database_path() -> str:
    """Get the path to the SQLite database file."""
    # Store the database in the user's home directory
    home_dir = pathlib.Path.home()
    app_dir = home_dir / ".pycodex"

    # Create the directory if it doesn't exist
    app_dir.mkdir(exist_ok=True)

    return str(app_dir / "pycodex.db")


def create_db_engine(db_path: Optional[str] = None) -> Engine:
    """Create and return a SQLAlchemy engine."""
    if db_path is None:
        db_path = get_database_path()

    # Create SQLite database with absolute path
    db_url = f"sqlite:///{db_path}"
    return create_engine(db_url)


def init_database(db_path: Optional[str] = None) -> Engine:
    """Initialize the database."""
    engine = create_db_engine(db_path)
    Base.metadata.create_all(engine)
    return engine
