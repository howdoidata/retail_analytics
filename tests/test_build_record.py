"""Checks for the D-1 build record: the walkthrough covers every stage, every story
record has the required sections and a status that matches the story index, and every
relative link (including #anchors) in the folder and the root docs resolves."""

import re
from pathlib import Path

import pytest

from retail_analytics.config import DOCS_DIR, REPO_ROOT

BUILD_RECORD = DOCS_DIR / "build-record"
STAGES = ("Idea", "Definition", "Planning", "Build", "Review", "Verification", "Production")
RECORD_SECTIONS = ("Story spec", "Change", "Review outcome", "CI run", "Status")
RECORD_STATUSES = ("Done", "In review", "In progress")
STATUS_LINE = re.compile(r"^\*\*Status:\*\* (Recorded|In progress|Pending: \S+)$", re.MULTILINE)
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")

STORY_RECORDS = sorted(p for p in (BUILD_RECORD / "stories").glob("*.md") if p.name != "_template.md")
MARKDOWN_FILES = sorted(BUILD_RECORD.rglob("*.md")) + [REPO_ROOT / "README.md", REPO_ROOT / "CONTRIBUTING.md"]


def headings(path: Path) -> list[str]:
    return re.findall(r"^## (.+?)\s*$", path.read_text(encoding="utf-8"), re.MULTILINE)


def section(path: Path, title: str) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(rf"^## {re.escape(title)}\s*$(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
    assert match, f"{path.name}: no section {title!r}"
    return match.group(1)


def slug(heading: str) -> str:
    """GitHub-style heading anchor: lowercase, punctuation dropped (hyphens kept), spaces to hyphens."""
    return re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")


def anchors(path: Path) -> set[str]:
    text = re.sub(r"^```.*?^```", "", path.read_text(encoding="utf-8"), flags=re.MULTILINE | re.DOTALL)
    return {slug(h) for h in re.findall(r"^#{1,6} (.+?)\s*$", text, re.MULTILINE)}


def test_walkthrough_has_every_stage_in_order() -> None:
    found = [h for h in headings(BUILD_RECORD / "README.md") if h in STAGES]
    assert found == list(STAGES)


def test_every_stage_has_a_status_line() -> None:
    text = (BUILD_RECORD / "README.md").read_text(encoding="utf-8")
    sections = re.split(r"^## ", text, flags=re.MULTILINE)
    for section in sections:
        title = section.splitlines()[0].strip() if section else ""
        if title in STAGES:
            assert STATUS_LINE.search(section), f"stage {title!r} has no status line"


def test_story_records_exist() -> None:
    assert {p.stem for p in STORY_RECORDS} >= {"C-1", "C-2", "C-3", "D-1"}


@pytest.mark.parametrize("record", STORY_RECORDS, ids=lambda p: p.stem)
def test_story_record_has_required_sections(record: Path) -> None:
    found = [h for h in headings(record) if h in RECORD_SECTIONS]
    assert found == list(RECORD_SECTIONS), record.name


@pytest.mark.parametrize("record", STORY_RECORDS, ids=lambda p: p.stem)
def test_story_status_matches_index(record: Path) -> None:
    body = section(record, "Status").strip()
    status = next((s for s in RECORD_STATUSES if body.startswith(f"**{s}.**")), None)
    assert status, f"{record.name}: Status must start with one of {RECORD_STATUSES}"
    rows = [
        line
        for line in (BUILD_RECORD / "README.md").read_text(encoding="utf-8").splitlines()
        if line.startswith("|") and f"(stories/{record.name})" in line
    ]
    assert len(rows) == 1, f"{record.name}: expected one story-index row"
    assert rows[0].rstrip(" |").split("|")[-1].strip() == status, f"{record.name}: index status differs"


@pytest.mark.parametrize("doc", MARKDOWN_FILES, ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_relative_links_resolve(doc: Path) -> None:
    for target in LINK.findall(doc.read_text(encoding="utf-8")):
        if re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith("#"):
            continue
        path, _, fragment = target.partition("#")
        linked = (doc.parent / path) if path else doc
        assert linked.exists(), f"{doc.name}: broken link {target}"
        if fragment:
            assert linked.suffix == ".md", f"{doc.name}: anchor on a non-markdown target {target}"
            assert fragment in anchors(linked), f"{doc.name}: broken anchor {target}"
