"""Checks for the C-10 data catalog: `render` and `missing_descriptions` on a hand-made manifest
(`tests/fixtures/catalog/manifest.json`) and broken copies of it, the `uv run catalog` command's write and
`--check` paths, and that the committed `CATALOG.md` is current for the real dbt project."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest

from retail_analytics import catalog
from retail_analytics.config import REPO_ROOT

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "catalog" / "manifest.json"
CHANNEL = "A canonical channel: Paid Search,\nEmail, or In-store."


@pytest.fixture
def manifest() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def write(tmp_path: Path, manifest: dict) -> Path:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def section(text: str, title: str) -> str:
    match = re.search(rf"^## {re.escape(title)}\n(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
    assert match, f"no section {title!r}"
    return match.group(1)


# ---- rendering ----------------------------------------------------------------------------------


def test_sections_in_order(manifest: dict) -> None:
    text = catalog.render(manifest)
    assert text.startswith("# Data catalog\n")
    assert "uv run catalog" in text.split("## ")[0] and "synthetic" in text.split("## ")[0]
    found = re.findall(r"^## (.+)$", text, re.MULTILINE)
    assert found == ["Business terms", "Sources", "Staging", "Intermediate", "Marts", "Seeds"]


def test_nodes_sorted_by_layer_then_name(manifest: dict) -> None:
    text = catalog.render(manifest)
    assert re.findall(r"^#{3,4} `([^`]+)`$", text, re.MULTILINE) == [
        "raw.customers", "raw.orders",
        "stg_customers", "stg_orders",
        "int_spend",
        "fct_signups",
        "channels",
    ]  # fmt: skip
    assert "not_null_stg_orders_id" not in text  # tests are not catalogued


def test_source_description_once(manifest: dict) -> None:
    sources = section(catalog.render(manifest), "Sources")
    assert sources.count("Source CSVs from the generator.") == 1
    assert (
        sources.index("### Source `raw`")
        < sources.index("Source CSVs")
        < sources.index("#### `raw.customers`")
    )


def test_column_tables_in_yaml_order(manifest: dict) -> None:
    marts = section(catalog.render(manifest), "Marts")
    assert "| Column | Description |\n|---|---|\n| `signups` | New customers. |\n| `channel` |" in marts


def test_glossary_has_each_project_term_once_sorted(manifest: dict) -> None:
    text = catalog.render(manifest)
    terms = section(text, "Business terms")
    assert re.findall(r'^<a id="([^"]+)"></a>$', terms, re.MULTILINE) == [
        "term-channel",
        "term-paid-channel",
        "term-visit",
    ]
    assert "__overview__" not in text and "Welcome to dbt docs" not in text
    for anchor in ("term-channel", "term-paid-channel", "term-visit"):
        assert text.count(f'id="{anchor}"') == 1


def test_shared_term_links_and_text_appears_once(manifest: dict) -> None:
    text = catalog.render(manifest)
    assert "| `channel` | [channel](#term-channel) Acquisition channel. |" in text
    assert "[channel](#term-channel) One row per channel." in text
    # only in the glossary: its own entry and the longer paid_channel entry that contains it
    assert text.count(CHANNEL) == section(text, "Business terms").count(CHANNEL) == 2
    assert "One row per visit. [visit](#term-visit)" in text
    assert text.count("One purchase visit.") == 1


def test_longest_block_replaced_first(manifest: dict) -> None:
    intermediate = section(catalog.render(manifest), "Intermediate")
    assert "| `channel` | [paid channel](#term-paid-channel) |" in intermediate
    assert "#term-channel)" not in intermediate


def test_pipes_escaped_and_newlines_folded(manifest: dict) -> None:
    text = catalog.render(manifest)
    assert "| `status` | Status: paid \\| refunded. |" in text
    assert "| `status` | Either paid \\| complete, lowercased. |" in text


def test_deterministic(manifest: dict) -> None:
    text = catalog.render(manifest)
    assert catalog.render(copy.deepcopy(manifest)) == text
    shuffled = copy.deepcopy(manifest)
    shuffled["metadata"] = {"dbt_version": "9.9.9", "generated_at": "2030-01-01", "invocation_id": "x"}
    for key in ("nodes", "sources", "docs"):
        shuffled[key] = dict(reversed(list(shuffled[key].items())))
    assert catalog.render(shuffled) == text
    assert text.endswith("\n") and not text.endswith("\n\n") and "\r" not in text


def test_unknown_model_layer_fails(manifest: dict) -> None:
    manifest["nodes"]["model.retail_analytics.stg_orders"]["fqn"] = ["retail_analytics", "stg_orders"]
    with pytest.raises(ValueError, match="stg_orders"):
        catalog.render(manifest)


# ---- missing descriptions -----------------------------------------------------------------------


def test_valid_manifest_has_no_missing(manifest: dict) -> None:
    assert catalog.missing_descriptions(manifest) == []


def test_every_missing_description_named(manifest: dict) -> None:
    manifest["nodes"]["model.retail_analytics.stg_orders"]["columns"]["status"]["description"] = ""
    manifest["nodes"]["model.retail_analytics.fct_signups"]["columns"]["signups"]["description"] = ""
    manifest["nodes"]["model.retail_analytics.int_spend"]["description"] = "  \n "
    manifest["nodes"]["seed.retail_analytics.channels"]["description"] = ""
    manifest["sources"]["source.retail_analytics.raw.orders"]["description"] = " "
    manifest["sources"]["source.retail_analytics.raw.customers"]["columns"]["id"]["description"] = ""
    manifest["nodes"]["seed.retail_analytics.channels"]["columns"]["channel"]["description"] = " "
    for table in manifest["sources"].values():
        table["source_description"] = "\n"
    assert catalog.missing_descriptions(manifest) == [
        "model.retail_analytics.fct_signups.signups",
        "model.retail_analytics.int_spend",
        "model.retail_analytics.stg_orders.status",
        "seed.retail_analytics.channels",
        "seed.retail_analytics.channels.channel",
        "source.retail_analytics.raw",
        "source.retail_analytics.raw.customers.id",
        "source.retail_analytics.raw.orders",
    ]


# ---- command ------------------------------------------------------------------------------------


def test_write_then_check_passes(manifest: dict, tmp_path: Path) -> None:
    path, out = write(tmp_path, manifest), tmp_path / "CATALOG.md"
    catalog.main(["--manifest", str(path), "--output", str(out)])
    assert out.read_bytes() == catalog.render(manifest).encode("utf-8")
    catalog.main(["--manifest", str(path), "--output", str(out), "--check"])  # no exit


@pytest.mark.parametrize(
    ("where", "unique_id"),
    [
        ("column", "model.retail_analytics.stg_customers.id"),
        ("model", "model.retail_analytics.stg_customers"),
        ("source", "source.retail_analytics.raw"),
    ],
)
def test_missing_description_fails_write_and_check(
    manifest: dict, tmp_path: Path, capsys: pytest.CaptureFixture[str], where: str, unique_id: str
) -> None:
    out = tmp_path / "CATALOG.md"
    out.write_text(catalog.render(manifest), encoding="utf-8")
    before = out.read_bytes()
    if where == "column":
        manifest["nodes"]["model.retail_analytics.stg_customers"]["columns"]["id"]["description"] = ""
    elif where == "model":
        manifest["nodes"]["model.retail_analytics.stg_customers"]["description"] = " \n"
    else:
        for table in manifest["sources"].values():
            table["source_description"] = "  "
    path = write(tmp_path, manifest)
    for extra in ([], ["--check"]):
        with pytest.raises(SystemExit) as exc:
            catalog.main(["--manifest", str(path), "--output", str(out), *extra])
        assert exc.value.code == 1
        assert re.search(rf"^  {re.escape(unique_id)}$", capsys.readouterr().err, re.MULTILINE)
    assert out.read_bytes() == before  # writing never happens with a missing description


def test_check_reports_missing_and_stale_together(
    manifest: dict, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest["nodes"]["model.retail_analytics.stg_customers"]["columns"]["id"]["description"] = ""
    with pytest.raises(SystemExit):
        catalog.main(
            ["--manifest", str(write(tmp_path, manifest)), "--output", str(tmp_path / "none.md"), "--check"]
        )
    err = capsys.readouterr().err
    assert "model.retail_analytics.stg_customers.id" in err and catalog.STALE_MESSAGE in err


def test_stale_catalog_fails(manifest: dict, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "CATALOG.md"
    out.write_text(catalog.render(manifest), encoding="utf-8")
    manifest["nodes"]["model.retail_analytics.stg_customers"]["columns"]["id"]["description"] = "Edited."
    with pytest.raises(SystemExit) as exc:
        catalog.main(["--manifest", str(write(tmp_path, manifest)), "--output", str(out), "--check"])
    assert exc.value.code == 1
    assert "CATALOG.md is out of date; run `uv run catalog`" in capsys.readouterr().err


def test_missing_catalog_fails(manifest: dict, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        catalog.main(
            [
                "--manifest",
                str(write(tmp_path, manifest)),
                "--output",
                str(tmp_path / "CATALOG.md"),
                "--check",
            ]
        )
    assert exc.value.code == 1
    assert catalog.STALE_MESSAGE in capsys.readouterr().err


# ---- real project -------------------------------------------------------------------------------


def test_committed_catalog_is_current() -> None:
    manifest = catalog.parse_manifest()
    assert catalog.missing_descriptions(manifest) == []
    committed = (REPO_ROOT / "CATALOG.md").read_bytes()
    assert committed == catalog.render(manifest).encode("utf-8"), catalog.STALE_MESSAGE
    text = committed.decode("utf-8")
    folded = re.sub(r"\s+", " ", text)
    blocks = catalog.doc_blocks(manifest)
    assert len(blocks) >= 13
    for name, block in blocks.items():
        assert text.count(f'<a id="term-{name.replace("_", "-")}"></a>') == 1, name
        assert folded.count(re.sub(r"\s+", " ", block)) == 1, name
