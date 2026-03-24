"""Integration tests for walk() using a temporary directory tree."""
import os
import pytest
from path_walker import walk, walk_first


@pytest.fixture()
def tree(tmp_path):
    """
    tmp_path/
      photos/
        2023/
          holiday.jpg
          beach.jpg
        2024/
          sunset.jpg
        readme.txt
      docs/
        report.pdf
        image.jpg
      data/
        a/
          bbb/
            result.csv
        b/
          bbb/
            result.csv
        c/
          other/
            notes.txt
    """
    def mk(*parts):
        p = tmp_path.joinpath(*parts)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('')

    mk('photos', '2023', 'holiday.jpg')
    mk('photos', '2023', 'beach.jpg')
    mk('photos', '2024', 'sunset.jpg')
    mk('photos', 'readme.txt')
    mk('docs', 'report.pdf')
    mk('docs', 'image.jpg')
    mk('data', 'a', 'bbb', 'result.csv')
    mk('data', 'b', 'bbb', 'result.csv')
    mk('data', 'c', 'other', 'notes.txt')

    return tmp_path


class TestSingleCapture:
    def test_dirs_containing_image(self, tree):
        # /{root}/{*}/image.jpg  ->  captures the single-level dir name
        pattern = str(tree) + '/{*}/image.jpg'
        results = walk(pattern)
        assert results == ['docs']

    def test_dirs_containing_jpg(self, tree):
        # photos/ only has 2023/, 2024/ subdirs and readme.txt directly
        # no .jpg files at the photos/ top level -> empty result
        pattern = str(tree) + '/photos/{*}.jpg'
        results = walk(pattern)
        assert results == []

    def test_star_in_capture(self, tree):
        # capture any .jpg directly under photos/
        # photos has: readme.txt, 2023/, 2024/ (no .jpg directly)
        pattern = str(tree) + '/photos/{*}/{*}.jpg'
        results = walk(pattern)
        # should return [['2023','holiday'],['2023','beach'],['2024','sunset']] (order may vary)
        assert len(results) == 3
        names = {tuple(r) for r in results}
        assert ('2023', 'holiday') in names
        assert ('2023', 'beach') in names
        assert ('2024', 'sunset') in names


class TestMultiLevelCapture:
    def test_star_slash_bbb(self, tree):
        # data/{*/bbb}  ->  captures 'a/bbb', 'b/bbb'
        pattern = str(tree) + '/data/{*/bbb}'
        results = walk(pattern)
        assert set(results) == {'a/bbb', 'b/bbb'}


class TestTwoCaptures:
    def test_two_captures(self, tree):
        # /{*}/{*}.jpg -> 2D list
        pattern = str(tree) + '/{*}/{*}.jpg'
        results = walk(pattern)
        assert isinstance(results[0], list)
        pairs = {tuple(r) for r in results}
        assert ('docs', 'image') in pairs

    def test_photos_subdir_two_captures(self, tree):
        pattern = str(tree) + '/photos/{*}/{*}.jpg'
        results = walk(pattern)
        assert len(results) == 3
        for r in results:
            assert isinstance(r, list)
            assert len(r) == 2


class TestNoCapture:
    def test_no_capture_returns_paths(self, tree):
        pattern = str(tree) + '/docs/*.pdf'
        results = walk(pattern)
        assert len(results) == 1
        assert results[0].endswith('report.pdf')


class TestWalkFirst:
    def test_first(self, tree):
        pattern = str(tree) + '/docs/{*}.pdf'
        result = walk_first(pattern)
        assert result == 'report'

    def test_first_no_match(self, tree):
        result = walk_first(str(tree) + '/nonexistent/{*}.jpg')
        assert result is None


class TestDoublestar:
    def test_doublestar_capture(self, tree):
        # find all .jpg files anywhere, capture the filename stem
        pattern = str(tree) + '/**/{*}.jpg'
        results = walk(pattern)
        names = set(results)
        assert 'holiday' in names
        assert 'beach' in names
        assert 'sunset' in names
        assert 'image' in names


# ---------------------------------------------------------------------------
# Inline capture group & literal-content capture
# ---------------------------------------------------------------------------

@pytest.fixture()
def inline_tree(tmp_path):
    """
    tmp_path/
      art/
        abc.png          <- matches {*}/ab{c}.png  (captures art, c)
        abd.png          <- does NOT match {*}/ab{c}.png  (d ≠ c)
        ababa/
          z.png          <- matches {*}/ababa/{z.png} (captures art, z.png)
          w.png          <- does NOT match {*}/ababa/{z.png} (w.png ≠ z.png)
      raw/
        abc.png          <- matches {*}/ab{c}.png  (captures raw, c)
        ababa/
          z.png          <- matches {*}/ababa/{z.png} (captures raw, z.png)
          z_extra.png    <- does NOT match (not exactly z.png)
    """
    def mk(*parts):
        p = tmp_path.joinpath(*parts)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('')

    mk('art', 'abc.png')
    mk('art', 'abd.png')
    mk('art', 'ababa', 'z.png')
    mk('art', 'ababa', 'w.png')
    mk('raw', 'abc.png')
    mk('raw', 'ababa', 'z.png')
    mk('raw', 'ababa', 'z_extra.png')

    return tmp_path


class TestInlineCaptureGroup:
    """
    {*}/ab{c}.png

    Regex: ^([^/]+)/ab(c)\\.png$

    The second capture {c} contains only the literal 'c', so it matches
    files named exactly 'abc.png' and captures the character 'c'.
    Files like 'abd.png' do not match.
    Returns a 2D list: [dir, 'c'].
    """

    def test_matches_abc_png(self, inline_tree):
        pattern = str(inline_tree) + '/{*}/ab{c}.png'
        results = walk(pattern)
        pairs = {tuple(r) for r in results}
        assert ('art', 'c') in pairs
        assert ('raw', 'c') in pairs

    def test_does_not_match_abd_png(self, inline_tree):
        pattern = str(inline_tree) + '/{*}/ab{c}.png'
        results = walk(pattern)
        dirs = {r[0] for r in results}
        # abd.png only exists under art/ — but it should not be captured
        # (all results must come from abc.png files)
        assert all(r[1] == 'c' for r in results)

    def test_exact_count(self, inline_tree):
        # Only art/abc.png and raw/abc.png qualify
        pattern = str(inline_tree) + '/{*}/ab{c}.png'
        results = walk(pattern)
        assert len(results) == 2

    def test_result_shape(self, inline_tree):
        pattern = str(inline_tree) + '/{*}/ab{c}.png'
        results = walk(pattern)
        for r in results:
            assert isinstance(r, list)
            assert len(r) == 2


class TestLiteralContentCapture:
    """
    {*}/ababa/{z.png}

    Regex: ^([^/]+)/ababa/(z\\.png)$

    The second capture {z.png} — the dot is escaped inside _glob_frag_to_regex,
    so it matches only the literal filename 'z.png'.
    Files like 'w.png' or 'z_extra.png' are excluded.
    Returns a 2D list: [dir, 'z.png'].
    """

    def test_matches_z_png(self, inline_tree):
        pattern = str(inline_tree) + '/{*}/ababa/{z.png}'
        results = walk(pattern)
        pairs = {tuple(r) for r in results}
        assert ('art', 'z.png') in pairs
        assert ('raw', 'z.png') in pairs

    def test_does_not_match_w_png(self, inline_tree):
        pattern = str(inline_tree) + '/{*}/ababa/{z.png}'
        results = walk(pattern)
        assert all(r[1] == 'z.png' for r in results)

    def test_does_not_match_z_extra_png(self, inline_tree):
        # z_extra.png has more chars after 'z' before '.png'
        pattern = str(inline_tree) + '/{*}/ababa/{z.png}'
        results = walk(pattern)
        filenames = {r[1] for r in results}
        assert 'z_extra.png' not in filenames

    def test_exact_count(self, inline_tree):
        # art/ababa/z.png and raw/ababa/z.png
        pattern = str(inline_tree) + '/{*}/ababa/{z.png}'
        results = walk(pattern)
        assert len(results) == 2

    def test_result_shape(self, inline_tree):
        pattern = str(inline_tree) + '/{*}/ababa/{z.png}'
        results = walk(pattern)
        for r in results:
            assert isinstance(r, list)
            assert len(r) == 2
