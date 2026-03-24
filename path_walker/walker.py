"""
Main walk() function for path_walker.
"""

import os
from typing import Any, List, Optional

from .pattern import pattern_to_regex


def walk(pattern: str, *, root: Optional[str] = None,
         bracket: str = "{}") -> List[Any]:
    """
    Walk the filesystem and return captured groups matched by *pattern*.

    Pattern syntax:
      *        matches any single path segment (no '/')
      **       matches zero or more path segments
      {P}      capture group — matches P and its match is returned
      [P]      same as {P} when ``bracket="[]"``

    Return value depends on the number of capture groups:
      0 captures  -> list of matched paths (str)
      1 capture   -> list of captured strings
      2+ captures -> list of lists (one inner list per match)

    Parameters
    ----------
    pattern : str
        Path pattern.  May be absolute or relative.
    root : str, optional
        Override the starting directory for the walk.
        If omitted the base is derived automatically from the pattern's
        literal prefix, falling back to the current working directory.
    bracket : str
        Two-character string specifying the capture bracket pair.
        ``"{}"`` (default) or ``"[]"``.
    """
    base_dir, regex, n_caps = pattern_to_regex(pattern, bracket)

    if root is not None:
        base_dir = root

    # Resolve to absolute so regex matching is stable
    base_dir = os.path.abspath(base_dir)

    # Re-build a regex anchored to the absolute base dir.
    _, regex, n_caps = pattern_to_regex(
        _abs_pattern(pattern, base_dir, bracket), bracket
    )

    results: List[Any] = []

    if not os.path.exists(base_dir):
        return results

    for dirpath, dirnames, filenames in os.walk(base_dir):
        for name in dirnames:
            _check(os.path.join(dirpath, name), regex, n_caps, results)
        for name in filenames:
            _check(os.path.join(dirpath, name), regex, n_caps, results)

    return results


def walk_first(pattern: str, **kwargs) -> Any:
    """Return the first match or None."""
    results = walk(pattern, **kwargs)
    return results[0] if results else None


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _check(path: str, regex, n_caps: int, results: list) -> None:
    norm = path.replace('\\', '/')
    m = regex.match(norm)
    if not m:
        return
    if n_caps == 0:
        results.append(norm)
    elif n_caps == 1:
        results.append(m.group(1))
    else:
        results.append(list(m.groups()))


def _abs_pattern(pattern: str, abs_base: str, bracket: str = "{}") -> str:
    """
    Replace the literal prefix of *pattern* with *abs_base* so that
    the compiled regex matches absolute paths produced by os.walk.

    Example:
        pattern  = './data/{*}/result.csv'
        abs_base = '/home/user/project/data'
        result   = '/home/user/project/data/{*}/result.csv'
    """
    norm = pattern.replace('\\', '/')
    abs_base_norm = abs_base.replace('\\', '/')

    wild_start = _first_wild_index(norm, bracket[0])
    if wild_start == -1:
        return abs_base_norm

    rest = norm[wild_start:]

    return abs_base_norm.rstrip('/') + '/' + rest.lstrip('/')


def _first_wild_index(s: str, open_char: str = '{') -> int:
    """Index of the first *, ?, or *open_char* in *s* (at top level).  -1 if none."""
    for i, ch in enumerate(s):
        if ch == open_char:
            return i
        elif ch == '*' or ch == '?':
            return i
    return -1
