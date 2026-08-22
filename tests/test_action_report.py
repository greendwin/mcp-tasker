import pytest

from tasker.base_types import Task
from tasker.cli._print_utils import ActionReportConfig, print_action_report
from tasker.utils import console


def test_action_report_renders_header_and_bullets(
    capsys: pytest.CaptureFixture[str],
) -> None:
    config = ActionReportConfig()
    config.add_item("s01", "First story")
    config.add_item("s02", "Second story")

    print_action_report("Adding to TODO", config)

    out = capsys.readouterr().out
    lines = [ln.strip() for ln in out.splitlines()]
    assert "Adding to TODO:" in lines
    assert "- s01" in lines
    assert "- s02" in lines
    # bullets carry the id only — titles belong to the preview render
    assert "First story" not in out
    assert "Second story" not in out


def test_action_report_annotates_deviating_outcome(
    capsys: pytest.CaptureFixture[str],
) -> None:
    config = ActionReportConfig()
    config.add_item("s01", "First story", outcome="already in todo")

    print_action_report("Adding to TODO", config)

    out = capsys.readouterr().out
    bullets = [ln.strip() for ln in out.splitlines() if ln.lstrip().startswith("- ")]
    assert len(bullets) == 1
    assert bullets[0].startswith("- s01")
    assert "(already in todo)" in bullets[0]


def test_action_report_omits_annotation_without_outcome(
    capsys: pytest.CaptureFixture[str],
) -> None:
    config = ActionReportConfig()
    config.add_item("s01", "First story")

    print_action_report("Adding to TODO", config)

    out = capsys.readouterr().out
    assert "- s01" in out
    assert "(" not in out


def test_action_report_add_task_renders_from_task(
    capsys: pytest.CaptureFixture[str],
) -> None:
    config = ActionReportConfig()
    config.add_task(Task(id="s01", title="First story"), outcome="already in todo")

    print_action_report("Adding to TODO", config)

    out = capsys.readouterr().out
    assert "- s01" in out
    assert "(already in todo)" in out
    assert "First story" not in out


def test_action_report_empty_prints_nothing(capsys: pytest.CaptureFixture[str]) -> None:
    config = ActionReportConfig()

    print_action_report("Adding to TODO", config)

    out = capsys.readouterr().out
    assert out == ""


def test_action_report_silent_under_json_output(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(console, "json_output", True)
    monkeypatch.setattr(console, "_json_output_obj", {})

    config = ActionReportConfig()
    config.add_item("s01", "First story", outcome="already in todo")

    print_action_report("Adding to TODO", config)

    out = capsys.readouterr().out
    assert out == ""
    assert console._json_output_obj == {}


def test_action_report_ignores_title_markup(
    capsys: pytest.CaptureFixture[str],
) -> None:
    config = ActionReportConfig()
    config.add_item("s01", "[red]danger[/red]")

    print_action_report("Adding to TODO", config)

    out = capsys.readouterr().out
    # the title is not rendered at all — neither literally nor as markup
    assert "danger" not in out
    assert "- s01" in out


def test_action_report_empty_outcome_treated_as_absent(
    capsys: pytest.CaptureFixture[str],
) -> None:
    config = ActionReportConfig()
    config.add_item("s01", "First story", outcome="")

    print_action_report("Adding to TODO", config)

    out = capsys.readouterr().out
    assert "- s01" in out
    assert "(" not in out
