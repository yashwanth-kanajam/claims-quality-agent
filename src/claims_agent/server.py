"""MCP server (stdio) exposing five read-only tools. Synthetic data only.

The dataset directory is fixed at start-up from CLAIMS_DATA_DIR. Tools take no
path argument, so a caller cannot point the server at ground-truth labels or
any other location, and nothing here opens a file for writing.
"""
import json
import os

from mcp.server.fastmcp import FastMCP

from . import checks

mcp = FastMCP("claims-quality")


def _run(tool):
    return json.dumps(checks.run_tool(os.environ["CLAIMS_DATA_DIR"], tool), sort_keys=True)


@mcp.tool()
def summarize_data_quality() -> str:
    """Shape of the five synthetic tables (present/missing tables and columns, row counts), whether the checks can run, and flag counts per check. Call this first."""
    return _run("summarize_data_quality")


@mcp.tool()
def detect_duplicates() -> str:
    """Exact duplicate records: every business field repeated, physical record_id excluded. All occurrences are flagged."""
    return _run("detect_duplicates")


@mcp.tool()
def check_broken_keys() -> str:
    """Broken foreign keys: enrollment/header/line rows whose member, provider or claim header does not exist."""
    return _run("check_broken_keys")


@mcp.tool()
def check_date_sequences() -> str:
    """Invalid date order under the synthetic contract (service start <= end <= received <= paid; lines within header; not before birth)."""
    return _run("check_date_sequences")


@mcp.tool()
def reconcile_header_to_line() -> str:
    """Header-to-line grain reconciliation: money-contract flags plus header, line and naive-join paid totals."""
    return _run("reconcile_header_to_line")


def main():
    if not os.environ.get("CLAIMS_DATA_DIR"):
        raise SystemExit("Set CLAIMS_DATA_DIR to a directory of synthetic claims CSVs.")
    mcp.run()


if __name__ == "__main__":
    main()
