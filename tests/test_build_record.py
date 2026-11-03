"""Checks for the D-1 build record: the walkthrough covers every stage, every story
record has the required sections, and every relative link in the folder resolves."""

import re
from pathlib import Path

import pytest

from retail_analytics.config import DOCS_DIR

BUILD_RECORD = DOCS_DIR / "build-record"
STAGES = ("Idea", "Definition", "Planning", "Build", "Review", "Verification", "Production")
RECORD_SECTIONS = ("Story spec", "Change", "Review outcome", "CI run", "Status")
STATUS_LINE = re.compile(r"^\*\*Status:\*\* (Recorded|In progress|Pending: \S+)$", re.MULTILINE)
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")

STORY_RECORDS = sorted(p for p in (BUILD_RECORD / "stories").glob("*.md") if p.name != "_template.md")
MARKDOWN_FILES = sorted(BUILD_RECORD.rglob("*.md"))


def headings(path: Path) -> list[str]:
    return re.findall(r"^## (.+?)\s*$", path.read_text(encoding="utf-8"), re.MULTILINE)


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
def test_story_is_indexed_in_walkthrough(record: Path) -> None:
    assert f"(stories/{record.name})" in (BUILD_RECORD / "README.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("doc", MARKDOWN_FILES, ids=lambda p: str(p.relative_to(BUILD_RECORD)))
def test_relative_links_resolve(doc: Path) -> None:
    for target in LINK.findall(doc.read_text(encoding="utf-8")):
        if re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith("#"):
            continue
        path = target.split("#", 1)[0]
        assert (doc.parent / path).exists(), f"{doc.name}: broken link {target}"
