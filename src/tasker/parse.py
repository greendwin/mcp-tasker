import re
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

from tasker.utils import read_text

from .base_types import EXTENDED_TASK_FILENAME, Task, TaskStatus, build_task_ref
from .exceptions import TaskValidateError

# ID: s<digits> or s<digits>t<digits> (t appears once; each level adds two digits)
# Cancelled tasks: ~~s01t01: Title~~ (new) or s01t01: ~~Title~~ (legacy)
_SUBTASK_RE = re.compile(r"^- \[(.)\] (?:~~)?(s\d+t(?:\d{2})+): (.+?)(?:~~)?$")
# Link-style: - [ ] [s01t01](s01t01-slug.md): Title
# or: - [ ] [s01t01](s01t01-slug/): Title
_LINK_SUBTASK_RE = re.compile(
    r"^- \[(.)\] (?:~~)?\[(s\d+t(?:\d{2})+)\]\(([^)]+)\): (.+?)(?:~~)?$"
)
_CHECKBOX_STATUS = {
    " ": TaskStatus.PENDING,
    "~": TaskStatus.IN_PROGRESS,
    "x": TaskStatus.DONE,
}


@dataclass
class ParsedRef:
    task_ref: str  # original value "id-slug or id"
    task_id: str
    slug: str | None
    parent_id: str
    root_id: str


def parse_task_ref(task_ref: str) -> ParsedRef:
    # strip optional slug from input like "s01t01-define-task-forms"
    m = re.match(r"^(s\d+(?:t(?:\d{2})+)?)", task_ref)
    if not m:
        raise TaskValidateError(f"Invalid task ref: {task_ref!r}", task_ref=task_ref)
    task_id = m.group(1)
    rest = task_ref[m.end() :]
    slug = rest[1:] if rest.startswith("-") else None

    if "t" not in task_id:
        root_id = task_id
        parent_id = task_id
    else:
        t_pos = task_id.index("t")
        root_id = task_id[:t_pos]
        digits_after_t = task_id[t_pos + 1 :]
        parent_id = task_id[:t_pos] if len(digits_after_t) == 2 else task_id[:-2]

    return ParsedRef(
        task_ref=task_ref,
        task_id=task_id,
        slug=slug,
        parent_id=parent_id,
        root_id=root_id,
    )


def find_common_ancestor(direct_refs: list[str]) -> str:
    assert len(direct_refs) > 0

    refs = [parse_task_ref(r) for r in direct_refs]

    if len(refs) == 1:
        return refs[0].task_id

    root_ids: list[str] = []
    for r in refs:
        if r.root_id not in root_ids:
            root_ids.append(r.root_id)

    # peak the latter root as a result
    root_id = root_ids.pop()

    # split each ID into per-level digit pairs after the 't' separator.
    digit_seqs: list[list[str]] = []
    for r in refs:
        if "t" in r.task_id:
            t_pos = r.task_id.index("t")
            digits = r.task_id[t_pos + 1 :]
            digit_seqs.append([digits[i : i + 2] for i in range(0, len(digits), 2)])
        else:
            digit_seqs.append([])

    common: list[str] = []
    for level_parts in zip(*digit_seqs):
        if len(set(level_parts)) != 1:
            break

        common.append(level_parts[0])

    if not common:
        return root_id

    return root_id + "t" + "".join(common)


def make_child_ref(parent_id: str, child_digits: str) -> str:
    """
    Build a child task ID by appending *child_digits* under *parent_id*.

    Root IDs (e.g. ``s01``) need a ``t`` separator; subtask IDs
    (e.g. ``s01t02``) already contain one so digits are appended directly.
    """
    prefix = parent_id if "t" in parent_id else parent_id + "t"
    return prefix + child_digits


@dataclass
class TaskDetectResult:
    task_ref: str
    task_id: str
    slug: str
    extended: bool
    content_path: Path


def detect_task_type(task_path: Path) -> TaskDetectResult:
    if task_path.is_dir():
        extended = True
        task_ref = task_path.name
        content_path = task_path / EXTENDED_TASK_FILENAME
    else:
        extended = False
        task_ref = task_path.stem
        content_path = task_path

    ref = parse_task_ref(task_ref)
    if ref.slug is None:
        raise TaskValidateError(
            f"Invalid task {task_path!r} with missing slug", task_ref=task_ref
        )

    return TaskDetectResult(
        task_ref=ref.task_ref,
        task_id=ref.task_id,
        slug=ref.slug,
        extended=extended,
        content_path=content_path,
    )


@dataclass
class ParsedSubtask:
    id: str
    slug: str | None
    ref: str
    title: str
    status: TaskStatus
    extended: bool


@dataclass
class _ParsedContent:
    id: str
    title: str
    slug: str | None
    description: str | None
    extra_sections: str | None
    status: TaskStatus
    subtasks: list[ParsedSubtask]


class ParseTaskResult(NamedTuple):
    task: Task
    subtasks: list[ParsedSubtask]


def parse_task(
    content: str, *, task_id: str, slug: str, extended: bool
) -> ParseTaskResult:
    parsed = _parse_content(content, task_ref=build_task_ref(task_id, slug))

    return ParseTaskResult(
        Task(
            # note: keep original `task_id`, it cannot be changed like a slug
            id=task_id,
            # note: parsed slug has higher priority over filename
            # (allows to rename file by editing slug value)
            slug=parsed.slug or slug,
            extended=extended,
            title=parsed.title,
            description=parsed.description,
            extra_sections=parsed.extra_sections,
            status=parsed.status,
        ),
        parsed.subtasks,
    )


def parse_task_file(path: Path) -> ParseTaskResult:
    tt = detect_task_type(path)
    content = read_text(tt.content_path)
    return parse_task(content, task_id=tt.task_id, slug=tt.slug, extended=tt.extended)


def _parse_subtask_line(line: str) -> ParsedSubtask | None:
    # Try link-style first: - [ ] [s01t01](s01t01-slug.md): Title
    ml = _LINK_SUBTASK_RE.match(line)
    if ml:
        checkbox, task_id, link_target, task_title = (
            ml.group(1),
            ml.group(2),
            ml.group(3),
            ml.group(4),
        )
        sub_status = _resolve_subtask_status(checkbox, line, task_title)
        task_title = _strip_strikethrough(task_title, line)
        extended = link_target.endswith("/")
        # extract slug from link target
        ref_str = link_target.rstrip("/").removesuffix(".md")
        ref = parse_task_ref(ref_str)
        return ParsedSubtask(
            id=task_id,
            slug=ref.slug,
            ref=ref_str,
            extended=extended,
            title=task_title,
            status=sub_status,
        )

    # Inline style: - [ ] s01t01: Title
    m = _SUBTASK_RE.match(line)
    if m:
        checkbox, task_id, task_title = m.group(1), m.group(2), m.group(3)
        sub_status = _resolve_subtask_status(checkbox, line, task_title)
        task_title = _strip_strikethrough(task_title, line)
        return ParsedSubtask(
            id=task_id,
            slug=None,
            ref=task_id,
            title=task_title,
            status=sub_status,
            extended=False,
        )

    return None


def _resolve_subtask_status(checkbox: str, line: str, title: str) -> TaskStatus:
    status = _CHECKBOX_STATUS.get(checkbox, TaskStatus.PENDING)
    if "~~" in line:
        status = TaskStatus.CANCELLED
    return status


def _strip_strikethrough(title: str, line: str) -> str:
    if "~~" not in line:
        return title
    # Strip legacy title-only strikethrough markers
    if title.startswith("~~") and title.endswith("~~"):
        return title[2:-2]
    if title.startswith("~~"):
        return title[2:]
    return title


def _parse_content(content: str, *, task_ref: str) -> _ParsedContent:
    lines = content.splitlines()

    if not lines or lines[0] != "---":
        raise TaskValidateError(
            "Missing front-matter: file must start with '---'", task_ref=task_ref
        )

    try:
        fm_end = lines.index("---", 1)
    except ValueError:
        raise TaskValidateError(
            "Unclosed front-matter: missing closing '---'", task_ref=task_ref
        )

    id_val = ""
    status = TaskStatus.PENDING
    slug = None
    for line in lines[1:fm_end]:
        if line.startswith("id:"):
            id_val = line.split(":", 1)[1].strip()
        elif line.startswith("status:"):
            status = TaskStatus(line.split(":", 1)[1].strip())
        elif line.startswith("slug:"):
            slug = line.split(":", 1)[1].strip()
        elif line.strip():
            key = line.split(":", 1)[0].strip()
            raise TaskValidateError(
                f"Unknown front-matter field {key!r}", task_ref=task_ref
            )

    # Body: everything after the closing ---
    body = lines[fm_end + 1 :]
    while body and not body[0].strip():
        body.pop(0)

    if not body:
        raise TaskValidateError("Missing title after front-matter", task_ref=task_ref)

    if not body[0].startswith("# "):
        raise TaskValidateError("Title must be a '# Heading' line", task_ref=task_ref)

    title = body[0][2:]

    # Split body after title into sections by ## headings
    # Each section is (heading_or_none, lines)
    sections: list[tuple[str | None, list[str]]] = []
    current_heading: str | None = None
    current_lines: list[str] = []

    for line in body[1:]:
        if line.startswith("## "):
            sections.append((current_heading, current_lines))
            current_heading = line
            current_lines = []
        else:
            current_lines.append(line)
    sections.append((current_heading, current_lines))

    # Extract description (text before any ## heading)
    description: str | None = None
    subtasks: list[ParsedSubtask] = []
    extra_parts: list[str] = []

    for heading, sec_lines in sections:
        if heading is None:
            # text before any heading = description
            desc_lines = _strip_blank_lines(sec_lines)
            description = "\n".join(desc_lines) or None
        elif heading == "## Subtasks":
            for line in sec_lines:
                if not line.strip():
                    continue
                parsed_sub = _parse_subtask_line(line)
                if parsed_sub is None:
                    raise TaskValidateError(
                        f"Invalid subtask line in '## Subtasks': {line!r}",
                        task_ref=task_ref,
                    )
                subtasks.append(parsed_sub)
        else:
            # preserve non-managed sections verbatim
            sec_text = _strip_blank_lines([heading] + sec_lines)
            extra_parts.append("\n".join(sec_text))

    extra_sections = "\n\n".join(extra_parts) or None

    return _ParsedContent(
        id=id_val,
        title=title,
        slug=slug,
        description=description,
        extra_sections=extra_sections,
        status=status,
        subtasks=subtasks,
    )


def _strip_blank_lines(lines: list[str]) -> list[str]:
    result = list(lines)
    while result and not result[0].strip():
        result.pop(0)
    while result and not result[-1].strip():
        result.pop()
    return result
