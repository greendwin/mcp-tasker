from __future__ import annotations

from tasker.cli import app
from tests.helpers import assert_invoke, create_task


class TestExactSlugMatch:
    def test_exact_slug_resolves(self) -> None:
        ref = create_task("Bugs")
        result = assert_invoke(app, ["view", "bugs"])
        assert ref.task_id in result.output

    def test_exact_short_slug_resolves(self) -> None:
        ref = create_task("Go")
        result = assert_invoke(app, ["view", "go"])
        assert ref.task_id in result.output


class TestPartialSlugMatch:
    def test_partial_match_three_chars(self) -> None:
        ref = create_task("Debugging tools")
        result = assert_invoke(app, ["view", "deb"])
        assert ref.task_id in result.output

    def test_partial_match_short_input_fails(self) -> None:
        create_task("Debugging tools")
        result = assert_invoke(app, ["view", "de"], expect_error=True)
        assert result.exit_code != 0


class TestAmbiguousMatch:
    def test_ambiguous_partial_raises_error(self) -> None:
        create_task("Bug tracker")
        create_task("Bug fixer")
        result = assert_invoke(app, ["view", "bug"], expect_error=True)
        assert "bug-tracker" in result.output or "bug" in result.output.lower()

    def test_exact_match_wins_over_partial(self) -> None:
        ref = create_task("Bug")
        create_task("Bug tracker")
        result = assert_invoke(app, ["view", "bug"])
        assert ref.task_id in result.output


class TestNoMatch:
    def test_no_match_raises_error(self) -> None:
        create_task("Something")
        result = assert_invoke(app, ["view", "nonexistent"], expect_error=True)
        assert result.exit_code != 0


class TestNameRefInCli:
    def test_view_command_uses_name(self) -> None:
        ref = create_task("Setup CI pipeline")
        result = assert_invoke(app, ["view", "setup-ci-pipeline"])
        assert ref.task_id in result.output
        assert "Setup CI pipeline" in result.output
