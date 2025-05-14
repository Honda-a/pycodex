import collections
import re
from pathlib import Path
from typing import Callable, List, Optional, Reversible, Tuple, Union

def handle_negation(file_path: Union[str, Path], rules: Reversible["IgnoreRule"]) -> bool: ...
def parse_gitignore(
    full_path: Union[str, Path], base_dir: Optional[Union[str, Path]] = None
) -> Callable[[Union[str, Path]], bool]: ...
def parse_gitignore_str(
    gitignore_str: str, base_dir: Union[str, Path]
) -> Callable[[Union[str, Path]], bool]: ...
def _parse_gitignore_lines(
    lines: Union[List[str], re.Pattern],
    full_path: Union[str, Path],
    base_dir: Union[str, Path],
) -> Callable[[Union[str, Path]], bool]: ...
def rule_from_pattern(
    pattern: str,
    base_path: Optional[Union[str, Path]] = None,
    source: Optional[Tuple[Union[str, Path], int]] = None,
) -> Optional["IgnoreRule"]: ...
def fnmatch_pathname_to_regex(
    pattern: str, directory_only: bool, negation: bool, anchored: bool = False
) -> str: ...
def _normalize_path(path: Union[str, Path]) -> Path: ...

class IgnoreRule(
    collections.namedtuple(
        "IgnoreRule_",
        [
            "pattern",
            "regex",  # Basic values
            "negation",
            "directory_only",
            "anchored",  # Behavior flags
            "base_path",  # Meaningful for gitignore-style behavior
            "source",  # (file, line) tuple for reporting
        ],
    )
):
    pattern: str
    regex: re.Pattern
    negation: bool
    directory_only: bool
    anchored: bool
    base_path: Optional[Path]
    source: Optional[Tuple[Union[str, Path], int]]

    def __str__(self) -> str: ...
    def __repr__(self) -> str: ...
    def match(self, abs_path: Union[str, Path]) -> bool: ...
