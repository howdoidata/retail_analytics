# data/export

The three marts exported as CSV for the dashboard (`<mart>.csv`), written by `uv run export` from the
DuckDB file that `uv run build` writes. Contents are gitignored; rebuild them with `uv run build`, then
`uv run export`. Shapes: [`docs/data-contracts.md`](../../docs/data-contracts.md#exports).
All values are simulated.
