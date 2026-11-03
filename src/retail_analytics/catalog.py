"""`uv run catalog`: write `CATALOG.md` from the dbt manifest; `--check` gates it in CI.

Every word of the catalog comes from the manifest (dbt YAML descriptions and doc blocks); nothing here
describes a model. `uv run catalog` parses the project into a temporary target path (no database needed) and
writes `CATALOG.md` at the repo root. `uv run catalog --check` fails when any source, seed, model, or declared
column has no description, or when the committed `CATALOG.md` differs from what the manifest
produces. The manifest only knows columns declared in YAML; that YAML columns match the built columns is
enforced by the layer tests (`test_every_node_is_described` in `tests/test_staging.py`,
`test_every_intermediate_node_is_described` in `tests/test_core_layers.py`, and each mart test file's
`information_schema` check).
`--manifest PATH` reads that manifest instead of parsing the project.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

from retail_analytics.config import DBT_DIR, REPO_ROOT

PROJECT = "retail_analytics"
CATALOG_PATH = REPO_ROOT / "CATALOG.md"
MODEL_LAYERS = (("staging", "Staging"), ("intermediate", "Intermediate"), ("marts", "Marts"))
STALE_MESSAGE = "CATALOG.md is out of date; run `uv run catalog`"

INTRO = """\
# Data catalog

Generated from the dbt project's descriptions and doc blocks; do not edit by hand. Regenerate with
`uv run catalog` (CI fails when this file is out of date). All data in this project is synthetic.

Business terms are defined once under [Business terms](#business-terms); descriptions elsewhere link to them.
"""


# ---- manifest access ----------------------------------------------------------------------------


def doc_blocks(manifest: dict) -> dict[str, str]:
    """The project's doc blocks, name -> text (dbt's own blocks, such as `__overview__`, are left out)."""
    return {
        d["name"]: d["block_contents"].strip()
        for d in manifest.get("docs", {}).values()
        if d.get("package_name") == PROJECT
    }


def _nodes(manifest: dict, resource_type: str) -> list[dict]:
    return [n for n in manifest.get("nodes", {}).values() if n.get("resource_type") == resource_type]


def _sources(manifest: dict) -> list[dict]:
    return list(manifest.get("sources", {}).values())


def _layer(model: dict) -> str:
    fqn = model.get("fqn", [])
    return fqn[1] if len(fqn) > 2 else ""


# ---- missing descriptions -----------------------------------------------------------------------


def _blank(text: str | None) -> bool:
    return not (text or "").strip()


def missing_descriptions(manifest: dict) -> list[str]:
    """Every source, source table, seed, model, or column with an empty or whitespace description:
    `unique_id` for a node, `unique_id.column` for a column."""
    missing: list[str] = []
    seen_sources: set[str] = set()
    for table in sorted(_sources(manifest), key=lambda t: t["unique_id"]):
        source_id = f"source.{table['package_name']}.{table['source_name']}"
        if source_id not in seen_sources:
            seen_sources.add(source_id)
            if _blank(table.get("source_description")):
                missing.append(source_id)
    nodes = _sources(manifest) + _nodes(manifest, "model") + _nodes(manifest, "seed")
    for node in sorted(nodes, key=lambda n: n["unique_id"]):
        if _blank(node.get("description")):
            missing.append(node["unique_id"])
        for column in node.get("columns", {}).values():
            if _blank(column.get("description")):
                missing.append(f"{node['unique_id']}.{column['name']}")
    return sorted(missing)


# ---- rendering ----------------------------------------------------------------------------------


def _anchor(term: str) -> str:
    return "term-" + term.replace("_", "-")


def _fold(text: str) -> str:
    """One line: every run of whitespace containing a line break becomes one space."""
    return re.sub(r"\s*\n\s*", " ", text.strip())


class _Linker:
    """Replaces each doc block's text with a link to its glossary entry, longest block first."""

    def __init__(self, blocks: dict[str, str]) -> None:
        self.pairs = sorted(
            (
                (text, f"[{name.replace('_', ' ')}](#{_anchor(name)})")
                for name, text in blocks.items()
                if text
            ),
            key=lambda pair: (-len(pair[0]), pair[0]),
        )

    def __call__(self, text: str | None) -> str:
        text = (text or "").strip()
        for block, link in self.pairs:
            text = text.replace(block, link)
        return _fold(text)


def _cell(text: str) -> str:
    return text.replace("|", "\\|")


def _entry(heading: str, node: dict, link: _Linker) -> list[str]:
    lines = [heading, "", link(node.get("description")), ""]
    columns = list(node.get("columns", {}).values())
    if columns:
        lines += ["| Column | Description |", "|---|---|"]
        lines += [f"| `{_cell(c['name'])}` | {_cell(link(c.get('description')))} |" for c in columns]
        lines.append("")
    return lines


def render(manifest: dict) -> str:
    """The catalog as Markdown: intro, business terms, sources, staging, intermediate, marts, seeds."""
    blocks = doc_blocks(manifest)
    link = _Linker(blocks)
    lines = [INTRO, "## Business terms", ""]
    for name in sorted(blocks):
        lines += [f'<a id="{_anchor(name)}"></a>', "", f"### {name.replace('_', ' ')}", "", blocks[name], ""]

    lines += ["## Sources", ""]
    by_source: dict[str, list[dict]] = {}
    for table in _sources(manifest):
        by_source.setdefault(table["source_name"], []).append(table)
    for source_name in sorted(by_source):
        tables = sorted(by_source[source_name], key=lambda t: t["name"])
        lines += [f"### Source `{source_name}`", "", link(tables[0].get("source_description")), ""]
        for table in tables:
            lines += _entry(f"#### `{source_name}.{table['name']}`", table, link)

    models = _nodes(manifest, "model")
    unknown = sorted(m["unique_id"] for m in models if _layer(m) not in dict(MODEL_LAYERS))
    if unknown:
        raise ValueError(f"models outside staging/intermediate/marts: {', '.join(unknown)}")
    for layer, title in MODEL_LAYERS:
        lines += [f"## {title}", ""]
        for model in sorted((m for m in models if _layer(m) == layer), key=lambda m: m["name"]):
            lines += _entry(f"### `{model['name']}`", model, link)

    lines += ["## Seeds", ""]
    for seed in sorted(_nodes(manifest, "seed"), key=lambda s: s["name"]):
        lines += _entry(f"### `{seed['name']}`", seed, link)

    return "\n".join(lines).rstrip("\n") + "\n"


# ---- command ------------------------------------------------------------------------------------


def parse_manifest() -> dict:
    """`dbt parse` with the repo-local profile into a temporary target path, then its manifest."""
    import os

    from dbt.cli.main import dbtRunner

    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path.cwd()
        os.chdir(REPO_ROOT)  # profiles.yml paths are relative to the repo root
        try:
            result = dbtRunner().invoke([
                "parse", "--quiet",
                "--project-dir", str(DBT_DIR),
                "--profiles-dir", str(DBT_DIR),
                "--target-path", str(Path(tmp) / "target"),
                "--log-path", str(Path(tmp) / "logs"),
            ])  # fmt: skip
        finally:
            os.chdir(cwd)
        if not result.success:
            raise SystemExit(f"dbt parse failed: {result.exception or 'see the errors above'}")
        return json.loads((Path(tmp) / "target" / "manifest.json").read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> None:
    """Entry point for `uv run catalog [--check] [--manifest PATH] [--output PATH]`."""
    parser = argparse.ArgumentParser(prog="catalog", description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check", action="store_true", help="fail if descriptions are missing or the file is stale"
    )
    parser.add_argument("--manifest", type=Path, help="read this manifest instead of running `dbt parse`")
    parser.add_argument(
        "--output", type=Path, default=CATALOG_PATH, help="catalog file (default: CATALOG.md)"
    )
    args = parser.parse_args(argv)

    if args.manifest:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    else:
        manifest = parse_manifest()

    failed = False
    missing = missing_descriptions(manifest)
    if missing:
        failed = True
        print(f"{len(missing)} without a description (add one in the dbt YAML):", file=sys.stderr)
        for item in missing:
            print(f"  {item}", file=sys.stderr)

    content = render(manifest).encode("utf-8")
    if args.check:
        if not args.output.is_file() or args.output.read_bytes() != content:
            failed = True
            print(STALE_MESSAGE, file=sys.stderr)
    elif not failed:
        args.output.write_bytes(content)
        print(f"wrote {args.output.name}")

    if failed:
        sys.exit(1)
