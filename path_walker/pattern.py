"""
Pattern parsing for path_walker.

Syntax:
  *    - matches any single path segment (no '/')
  **   - matches zero or more path segments
  {P}  - capture group: matches pattern P and returns the matched portion
         P may itself contain *, **, and '/' (multi-level capture)
  [P]  - same as {P} when bracket="[]" is used

The capture bracket style is configurable via the ``bracket`` parameter
(default ``"{}"``).  Only the chosen bracket pair is treated as capture
delimiters; the other pair is treated as literal characters.

Examples:
  /{*}/image.jpg     -> capture single dir that contains image.jpg
  ./xxx/{*/bbb}      -> capture */bbb subtrees under xxx/
  /{*}/{*}.jpg       -> two captures -> 2D results
"""

import re


def _find_close_brace(s: str, open_pos: int,
                      open_char: str = '{', close_char: str = '}') -> int:
    depth = 0
    for i in range(open_pos, len(s)):
        if s[i] == open_char:
            depth += 1
        elif s[i] == close_char:
            depth -= 1
            if depth == 0:
                return i
    raise ValueError(f"Unmatched {open_char!r} in pattern: {s!r}")


def _glob_frag_to_regex(frag: str) -> str:
    """
    Convert a glob fragment (may contain * and ** and /) to a regex string.
    Used for the *inside* of a capture group {}.
    """
    result = []
    i = 0
    while i < len(frag):
        if frag[i:i+2] == '**':
            result.append('.+')     # one or more chars, including /
            i += 2
        elif frag[i] == '*':
            result.append('[^/]+')  # one or more non-separator chars
            i += 1
        elif frag[i] == '?':
            result.append('[^/]')
            i += 1
        else:
            result.append(re.escape(frag[i]))
            i += 1
    return ''.join(result)


def pattern_to_regex(pattern: str, bracket: str = "{}"):
    """
    Convert a path_walker pattern to a (base_dir, compiled_regex, n_captures) tuple.

    The regex has one capture group per bracket pair in the pattern.
    base_dir is the longest literal prefix (no wildcards, no captures).

    Parameters
    ----------
    bracket : str
        Two-character string whose first character is the opening bracket and
        second is the closing bracket.  ``"{}"`` (default) or ``"[]"``.
    """
    open_char, close_char = bracket[0], bracket[1]

    s = pattern.replace('\\', '/')
    n = len(s)
    regex_parts = []
    n_caps = 0

    # ---- build regex in one pass ----
    i = 0
    while i < n:
        # Capture group
        if s[i] == open_char:
            j = _find_close_brace(s, i, open_char, close_char)
            inner = s[i+1:j]
            regex_parts.append('(' + _glob_frag_to_regex(inner) + ')')
            n_caps += 1
            i = j + 1

        # /**/  -> zero-or-more intermediate directories (keeps surrounding /)
        elif s[i:i+4] == '/**/':
            regex_parts.append('/(?:[^/]+/)*')
            i += 4

        # /**  trailing
        elif s[i:i+3] == '/**':
            regex_parts.append('(?:/[^/]+)*')
            i += 3

        # **/  leading or after content
        elif s[i:i+3] == '**/':
            regex_parts.append('(?:[^/]+/)*')
            i += 3

        # **
        elif s[i:i+2] == '**':
            regex_parts.append('.*')
            i += 2

        # *
        elif s[i] == '*':
            regex_parts.append('[^/]+')
            i += 1

        # ?
        elif s[i] == '?':
            regex_parts.append('[^/]')
            i += 1

        # ordinary character (including / and .)
        else:
            regex_parts.append(re.escape(s[i]))
            i += 1

    full_regex = '^' + ''.join(regex_parts) + '$'
    compiled = re.compile(full_regex)

    # ---- find base directory (literal prefix before first wildcard / capture) ----
    base_dir = _extract_base_dir(s, open_char)

    return base_dir, compiled, n_caps


def _split_top_level(s: str, sep: str = '/',
                     open_char: str = '{', close_char: str = '}'):
    """Split *s* by *sep*, but ignore seps inside the active bracket pair."""
    tokens = []
    depth = 0
    buf = []
    for ch in s:
        if ch == open_char:
            depth += 1
            buf.append(ch)
        elif ch == close_char:
            depth -= 1
            buf.append(ch)
        elif ch == sep and depth == 0:
            tokens.append(''.join(buf))
            buf = []
        else:
            buf.append(ch)
    tokens.append(''.join(buf))
    return tokens


def _extract_base_dir(norm: str, open_char: str = '{') -> str:
    """Return the longest literal prefix path segment (no * ? or *open_char*)."""
    close_char = '}' if open_char == '{' else ']'
    tokens = _split_top_level(norm, '/', open_char, close_char)

    base_tokens = []
    for tok in tokens:
        if any(c in tok for c in ('*', '?', open_char)):
            break
        base_tokens.append(tok)

    base = '/'.join(base_tokens)

    if not base:
        if norm.startswith('/'):
            return '/'
        return '.'

    return base
