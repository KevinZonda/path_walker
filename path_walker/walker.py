"""
Main walk() function for path_walker.
"""

import os
from typing import Any, List, Optional

from .pattern import pattern_to_regex


def walk(pattern: str, *, root: Optional[str] = None) -> List[Any]:
    """
    Walk the filesystem and return captured groups matched by *pattern*.

    Pattern syntax:
      *        matches any single path segment (no '/')
      **       matches zero or more path segments
      {P}      capture group — matches P and its match is returned

    Return value depends on the number of {} groups:
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
    """
    base_dir, regex, n_caps = pattern_to_regex(pattern)

    if root is not None:
        base_dir = root

    # Resolve to absolute so regex matching is stable
    base_dir = os.path.abspath(base_dir)

    # Re-build a regex anchored to the absolute base dir.
    # We do this by re-parsing the pattern with the resolved prefix.
    # Simpler: just normalise paths during the walk and match directly.

    _, regex, n_caps = pattern_to_regex(_abs_pattern(pattern, base_dir))

    results: List[Any] = []

    if not os.path.exists(base_dir):
        return results

    for dirpath, dirnames, filenames in os.walk(base_dir):
        # Check directories themselves (pattern may target a dir)
        for name in dirnames:
            _check(os.path.join(dirpath, name), regex, n_caps, results)
        # Check files
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


def _abs_pattern(pattern: str, abs_base: str) -> str:
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

    # Find where the first wildcard / capture starts
    wild_start = _first_wild_index(norm)
    if wild_start == -1:
        # No wildcards: pattern is a literal path
        return abs_base_norm

    # The literal prefix in the original pattern (may be relative like './data')
    # We simply drop it and prepend the resolved abs_base.
    literal_prefix = norm[:wild_start]
    rest = norm[wild_start:]  # starts with wildcard or {

    # rest might start with '/' if the pattern was '/{*}/...'
    # abs_base already covers everything up to (not including) the first wildcard
    return abs_base_norm.rstrip('/') + '/' + rest.lstrip('/')


def _first_wild_index(s: str) -> int:
    """Index of the first *, ?, or { in s (at top level).  -1 if none."""
    depth = 0
    for i, ch in enumerate(s):
        if ch == '{':
            return i  # the { itself is the start
        elif ch == '*' or ch == '?':
            return i
    return -1
