import pytest

from tasker.base_types import Task
from tasker.cli._print_utils import ActionReportConfig, print_action_report
from tasker.utils import console


def test_action_report_renders_header_and_bullets(
    capsys: pytest.CaptureFixture[str],
) -> None:
    config = ActionReportConfig(action="Adding to TODO")
    config.add_item("s01", "First story")
    config.add_item("s02", "Second story")

    print_action_report(config)

    out = capsys.readouterr().out
    assert "Adding to TODO:" in out
    assert "- s01: First story" in out
    assert "- s02: Second story" in out


def test_action_report_annotates_deviating_outcome(
    capsys: pytest.CaptureFixture[str],
) -> None:
    config = ActionReportConfig(action="Adding to TODO")
    config.add_item("s01", "First story", outcome="already in todo")

    print_action_report(config)

    out = capsys.readouterr().out
    assert "- s01: First story" in out
    assert "(already in todo)" in out


def test_action_report_omits_annotation_without_outcome(
    capsys: pytest.CaptureFixture[str],
) -> None:
    config = ActionReportConfig(action="Adding to TODO")
    config.add_item("s01", "First story")

    print_action_report(config)

    out = capsys.readouterr().out
    assert "- s01: First story" in out
    assert "(" not in out


def test_action_report_add_task_renders_from_task(
    capsys: pytest.CaptureFixture[str],
) -> None:
    config = ActionReportConfig(action="Adding to TODO")
    config.add_task(Task(id="s01", title="First story"), outcome="already in todo")

    print_action_report(config)

    out = capsys.readouterr().out
    assert "- s01: First story" in out
    assert "(already in todo)" in out


def test_action_report_empty_prints_nothing(capsys: pytest.CaptureFixture[str]) -> None:
    config = ActionReportConfig(action="Adding to TODO")

    print_action_report(config)

    out = capsys.readouterr().out
    assert out == ""


def test_action_report_silent_under_json_output(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(console, "json_output", True)
    monkeypatch.setattr(console, "_json_output_obj", {})

    config = ActionReportConfig(action="Adding to TODO")
    config.add_item("s01", "First story", outcome="already in todo")

    print_action_report(config)

    out = capsys.readouterr().out
    assert out == ""
    assert console._json_output_obj == {}


def test_action_report_escapes_markup_in_title(
    capsys: pytest.CaptureFixture[str],
) -> None:
    config = ActionReportConfig(action="Adding to TODO")
    config.add_item("s01", "[red]danger[/red]")

    print_action_report(config)

    out = capsys.readouterr().out
    assert "[red]danger[/red]" in out


def test_action_report_empty_outcome_treated_as_absent(
    capsys: pytest.CaptureFixture[str],
) -> None:
    config = ActionReportConfig(action="Adding to TODO")
    config.add_item("s01", "First story", outcome="")

    print_action_report(config)

    out = capsys.readouterr().out
    assert "- s01: First story" in out
    assert "(" not in out
