"""Tests for git utilities: branch management and diff commands."""

import os
import tempfile

from pilot.git import derive_branch_name


def test_derive_branch_name_from_title():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "input.md")
        with open(path, "w") as f:
            f.write("# Add user authentication\n\nSome details here.\n")
        assert derive_branch_name(path) == "pilot/add-user-authentication"


def test_derive_branch_name_strips_markdown_heading():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "input.md")
        with open(path, "w") as f:
            f.write("## Fix the login bug\n")
        assert derive_branch_name(path) == "pilot/fix-the-login-bug"


def test_derive_branch_name_slugifies_special_chars():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "input.md")
        with open(path, "w") as f:
            f.write("Add OAuth2 & JWT support!!!\n")
        assert derive_branch_name(path) == "pilot/add-oauth2-jwt-support"


def test_derive_branch_name_truncates_long_titles():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "input.md")
        with open(path, "w") as f:
            f.write("A" * 200 + "\n")
        result = derive_branch_name(path)
        # pilot/ prefix + slug, slug capped at 50
        assert result.startswith("pilot/")
        slug = result[len("pilot/"):]
        assert len(slug) <= 50


def test_derive_branch_name_skips_empty_lines():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "input.md")
        with open(path, "w") as f:
            f.write("\n\n\n# Real title here\n")
        assert derive_branch_name(path) == "pilot/real-title-here"


def test_derive_branch_name_skips_html_comments():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "input.md")
        with open(path, "w") as f:
            f.write("<!-- draft -->\nActual feature name\n")
        assert derive_branch_name(path) == "pilot/actual-feature-name"


def test_derive_branch_name_fallback_on_missing_file():
    result = derive_branch_name("/nonexistent/path/input.md")
    assert result.startswith("pilot/run-")


def test_derive_branch_name_fallback_on_empty_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "input.md")
        with open(path, "w") as f:
            f.write("")
        result = derive_branch_name(path)
        assert result.startswith("pilot/run-")
