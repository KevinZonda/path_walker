"""Unit tests for pattern parsing and regex compilation."""
import re
import pytest
from path_walker.pattern import pattern_to_regex, _glob_frag_to_regex


class TestGlobFragToRegex:
    def test_literal(self):
        assert re.fullmatch(_glob_frag_to_regex('hello'), 'hello')

    def test_star(self):
        r = _glob_frag_to_regex('*')
        assert re.fullmatch(r, 'foo')
        assert not re.fullmatch(r, 'foo/bar')  # * doesn't cross /

    def test_doublestar(self):
        r = _glob_frag_to_regex('**')
        assert re.fullmatch(r, 'a/b/c')

    def test_mixed(self):
        r = _glob_frag_to_regex('*/bbb')
        assert re.fullmatch(r, 'aaa/bbb')
        assert not re.fullmatch(r, 'bbb')
        assert not re.fullmatch(r, 'aaa/bbb/ccc')


class TestPatternToRegex:
    def _match(self, pattern, path):
        _, regex, _ = pattern_to_regex(pattern)
        return regex.match(path.replace('\\', '/'))

    def _groups(self, pattern, path):
        _, regex, _ = pattern_to_regex(pattern)
        m = regex.match(path.replace('\\', '/'))
        return m.groups() if m else None

    def _n_caps(self, pattern):
        _, _, n = pattern_to_regex(pattern)
        return n

    # ---- basic matching ----
    def test_literal_path(self):
        assert self._match('/foo/bar.txt', '/foo/bar.txt')
        assert not self._match('/foo/bar.txt', '/foo/baz.txt')

    def test_star_segment(self):
        assert self._match('/foo/*/bar.txt', '/foo/abc/bar.txt')
        assert not self._match('/foo/*/bar.txt', '/foo/a/b/bar.txt')

    def test_doublestar_zero_segments(self):
        assert self._match('/foo/**/bar.txt', '/foo/bar.txt')

    def test_doublestar_one_segment(self):
        assert self._match('/foo/**/bar.txt', '/foo/x/bar.txt')

    def test_doublestar_many_segments(self):
        assert self._match('/foo/**/bar.txt', '/foo/x/y/z/bar.txt')

    # ---- capture groups ----
    def test_single_capture_star(self):
        assert self._n_caps('/{*}/image.jpg') == 1
        g = self._groups('/{*}/image.jpg', '/photos/image.jpg')
        assert g == ('photos',)

    def test_no_match_single_capture(self):
        assert self._groups('/{*}/image.jpg', '/photos/sub/image.jpg') is None

    def test_multi_level_capture(self):
        assert self._n_caps('./xxx/{*/bbb}') == 1
        g = self._groups('./xxx/{*/bbb}', './xxx/abc/bbb')
        assert g == ('abc/bbb',)

    def test_two_captures(self):
        assert self._n_caps('/{*}/{*}.jpg') == 2
        g = self._groups('/{*}/{*}.jpg', '/photos/sunset.jpg')
        assert g == ('photos', 'sunset')

    def test_two_captures_no_match(self):
        assert self._groups('/{*}/{*}.jpg', '/photos/sub/sunset.jpg') is None

    def test_capture_with_suffix(self):
        g = self._groups('/{*}/{*}.jpg', '/2024/holiday.jpg')
        assert g == ('2024', 'holiday')

    # ---- base dir extraction ----
    def test_base_dir_relative(self):
        base, _, _ = pattern_to_regex('./data/{*}/result.csv')
        assert base == './data'

    def test_base_dir_absolute(self):
        base, _, _ = pattern_to_regex('/home/user/{*}/file.txt')
        assert base == '/home/user'

    def test_base_dir_root(self):
        base, _, _ = pattern_to_regex('/{*}/image.jpg')
        assert base == '/'

    def test_base_dir_no_wildcard(self):
        base, _, _ = pattern_to_regex('/foo/bar/baz.txt')
        assert base == '/foo/bar/baz.txt'
