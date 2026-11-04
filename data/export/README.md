# data/export

The three marts exported as CSV for the dashboard (`<mart>.csv`), written from the DuckDB file that
`uv run build` writes. Contents are gitignored and rebuilt by `uv run build`, whose last step is the
export; `uv run export` repeats just that step.
Shapes: [`docs/data-contracts.md`](../../docs/data-contracts.md#exports).
All values are simulated.
