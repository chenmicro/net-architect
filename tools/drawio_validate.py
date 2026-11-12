#!/usr/bin/env python3
"""Validate draw.io XML and the topology relationships encoded in it.

The validator checks every page after decoding it, so compressed and plain
pages receive the same structural checks.  It does not inspect or require SVG
exports.  ``xmllint``/the repository schema are an optional additional check;
the topology checks remain available when that external command is absent.

Examples::

    python tools/drawio_validate.py diagram.drawio
    python tools/drawio_validate.py diagram.drawio --no-schema
    python tools/drawio_validate.py diagram.drawio \
        --complete-bipartite 2,3 9,10,11,12
"""

from __future__ import annotations

import argparse
import copy
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional
import xml.etree.ElementTree as ET

try:
    from drawio_parse import Cell, Document, DrawioParseError, Page, load_document
except ImportError:  # pragma: no cover - supports ``python -m tools...``
    from .drawio_parse import Cell, Document, DrawioParseError, Page, load_document


DEFAULT_SCHEMA = Path(__file__).resolve().parents[1] / "plugins" / "drawio-mcp" / "shared" / "mxfile.xsd"

# Legend sample lines illustrate a line style and connect nothing; they are the
# only edges allowed to float, and only inside the container with this ID.
LEGEND_ID = "legend"


@dataclass
class Issue:
    severity: str
    message: str
    page: Optional[Page] = None


def _issue(issues: list[Issue], severity: str, message: str, page: Optional[Page] = None) -> None:
    issues.append(Issue(severity, message, page))


def _page_by_selector(document: Document, selector: str) -> list[Page]:
    try:
        number = int(selector)
    except ValueError:
        matches = [page for page in document.pages if selector in {page.name, page.id}]
    else:
        matches = [document.pages[number - 1]] if 1 <= number <= len(document.pages) else []
    return matches


def select_pages(document: Document, selectors: Optional[list[str]], issues: Optional[list[Issue]] = None) -> list[Page]:
    """Select pages by 1-based number, name, or page ID."""

    if not selectors:
        return list(document.pages)
    selected: list[Page] = []
    for selector in selectors:
        matches = _page_by_selector(document, selector)
        if not matches:
            if issues is not None:
                _issue(issues, "error", f"page selector {selector!r} did not match a page")
            continue
        for page in matches:
            if all(page.index != previous.index for previous in selected):
                selected.append(page)
    return selected


def _id_list(specification: str) -> list[str]:
    """Expand comma-separated IDs and simple numeric ranges.

    A numeric range is only recognized when both ends are decimal integers;
    IDs containing ordinary draw.io hyphens remain literal IDs.
    """

    result: list[str] = []
    for token in specification.split(","):
        token = token.strip()
        if not token:
            continue
        match = re.fullmatch(r"(-?\d+)\s*-\s*(-?\d+)", token)
        if match and not token.startswith("-"):
            start, end = int(match.group(1)), int(match.group(2))
            step = 1 if end >= start else -1
            result.extend(str(number) for number in range(start, end + step, step))
        else:
            result.append(token)
    return result


def _check_root_and_ids(page: Page, issues: list[Issue]) -> dict[str, Cell]:
    cells = page.cells
    ids = [cell.id for cell in cells]
    empty_positions = [index + 1 for index, cell_id in enumerate(ids) if cell_id is None or not cell_id.strip()]
    if empty_positions:
        _issue(issues, "error", f"cell IDs must be nonempty (cell positions: {', '.join(map(str, empty_positions))})", page)

    counts = Counter(cell_id for cell_id in ids if cell_id is not None and cell_id.strip())
    for cell_id, count in sorted(counts.items()):
        if count > 1:
            _issue(issues, "error", f"cell ID {cell_id!r} is duplicated {count} times", page)

    by_id: dict[str, Cell] = {}
    for cell in cells:
        if cell.id is not None and cell.id.strip() and cell.id not in by_id:
            by_id[cell.id] = cell

    for required in ("0", "1"):
        if required not in by_id:
            _issue(issues, "error", f"required root cell id={required!r} is missing", page)

    root = by_id.get("0")
    if root is not None:
        if root.parent not in (None, ""):
            _issue(issues, "error", f"root cell 0 must not have a parent (found {root.parent!r})", page)
        if root.vertex or root.edge:
            _issue(issues, "error", "root cell 0 must not be marked vertex or edge", page)

    layer = by_id.get("1")
    if layer is not None:
        if layer.parent != "0":
            _issue(issues, "error", f"default layer cell 1 must have parent='0' (found {layer.parent!r})", page)
        if layer.vertex or layer.edge:
            _issue(issues, "error", "default layer cell 1 must not be marked vertex or edge", page)

    for cell in cells:
        if cell.id == "0":
            continue
        if not cell.parent:
            _issue(issues, "error", f"cell {cell.id or '<missing>'!r} has no parent reference", page)
        elif cell.parent not in by_id:
            _issue(issues, "error", f"cell {cell.id or '<missing>'!r} references missing parent {cell.parent!r}", page)

    # A parent cycle prevents draw.io from constructing a valid hierarchy and
    # is easy to diagnose here even though it is not needed for edge checks.
    for cell in cells:
        if cell.id is None or cell.id not in by_id:
            continue
        seen: set[str] = set()
        current: Optional[str] = cell.id
        while current in by_id and current not in seen:
            seen.add(current)
            current = by_id[current].parent
        if current in seen:
            _issue(issues, "error", f"parent cycle detected from cell {cell.id!r}", page)
    return by_id


def _in_legend(cell: Cell, by_id: dict[str, Cell]) -> bool:
    seen: set[str] = set()
    current = cell.parent
    while current and current not in seen:
        if current == LEGEND_ID:
            return True
        seen.add(current)
        parent = by_id.get(current)
        current = parent.parent if parent is not None else None
    return False


def _check_edges(page: Page, by_id: dict[str, Cell], issues: list[Issue]) -> None:
    for edge in page.edges:
        edge_name = edge.id or "<missing>"
        if edge.geometry is None:
            _issue(issues, "error", f"edge {edge_name!r} has no mxGeometry child", page)
        elif edge.geometry.attrs.get("as") not in (None, "geometry"):
            _issue(issues, "warning", f"edge {edge_name!r} mxGeometry has as={edge.geometry.attrs.get('as')!r}, expected 'geometry'", page)

        for terminal_name, terminal_id in (("source", edge.source), ("target", edge.target)):
            if not terminal_id:
                # Floating edges are legal draw.io objects, but a link that is
                # not attached to both ends cannot be read back as an
                # adjacency.  Only legend samples may float.
                if not _in_legend(edge, by_id):
                    _issue(
                        issues,
                        "error",
                        f"edge {edge_name!r} has no {terminal_name} terminal (only edges inside the {LEGEND_ID!r} container may float)",
                        page,
                    )
                continue
            terminal = by_id.get(terminal_id)
            if terminal is None:
                _issue(issues, "error", f"edge {edge_name!r} {terminal_name}={terminal_id!r} does not resolve to a cell", page)
            elif not terminal.vertex:
                _issue(issues, "error", f"edge {edge_name!r} {terminal_name}={terminal_id!r} does not resolve to a vertex", page)

        if edge.geometry is not None:
            point_roles = {point.attrs.get("as") for point in edge.geometry.points}
            if edge.source and "sourcePoint" in point_roles:
                _issue(issues, "warning", f"edge {edge_name!r} has a stale sourcePoint despite a connected source terminal", page)
            if edge.target and "targetPoint" in point_roles:
                _issue(issues, "warning", f"edge {edge_name!r} has a stale targetPoint despite a connected target terminal", page)


def _resolve_vertex_set(specification: str, role: str, page: Page, by_id: dict[str, Cell], issues: list[Issue]) -> set[str]:
    ids = _id_list(specification)
    resolved: set[str] = set()
    for cell_id in ids:
        cell = by_id.get(cell_id)
        if cell is None:
            _issue(issues, "error", f"complete-bipartite {role} set references missing cell {cell_id!r}", page)
        elif not cell.vertex:
            _issue(issues, "error", f"complete-bipartite {role} set member {cell_id!r} is not a vertex", page)
        else:
            resolved.add(cell_id)
    if not ids:
        _issue(issues, "error", f"complete-bipartite {role} set is empty", page)
    return resolved


def check_complete_bipartite(page: Page, by_id: dict[str, Cell], spines_spec: str, leaves_spec: str, issues: list[Issue]) -> None:
    spines = _resolve_vertex_set(spines_spec, "first", page, by_id, issues)
    leaves = _resolve_vertex_set(leaves_spec, "second", page, by_id, issues)
    overlap = spines & leaves
    if overlap:
        _issue(issues, "error", f"complete-bipartite sets overlap: {', '.join(sorted(overlap))}", page)
    if not spines or not leaves:
        return

    expected = {(spine, leaf) for spine in spines for leaf in leaves}
    pair_counts: Counter[tuple[str, str]] = Counter()
    unexpected_internal: list[tuple[str, str]] = []
    for edge in page.edges:
        if not edge.source or not edge.target:
            continue
        source, target = edge.source, edge.target
        if source in spines and target in leaves:
            pair_counts[(source, target)] += 1
        elif target in spines and source in leaves:
            pair_counts[(target, source)] += 1
        elif (source in spines and target in spines) or (source in leaves and target in leaves):
            unexpected_internal.append((source, target))

    missing = sorted(expected - set(pair_counts))
    duplicates = sorted((pair, count) for pair, count in pair_counts.items() if count > 1)
    if missing:
        rendered = ", ".join(f"{left}<->{right}" for left, right in missing)
        _issue(issues, "error", f"complete-bipartite coverage is incomplete: missing {len(missing)} pair(s): {rendered}", page)
    if unexpected_internal:
        rendered = ", ".join(f"{left}<->{right}" for left, right in unexpected_internal)
        _issue(issues, "error", f"complete-bipartite coverage has {len(unexpected_internal)} intra-set edge(s): {rendered}", page)
    if duplicates:
        rendered = ", ".join(f"{left}<->{right} ({count} edges)" for (left, right), count in duplicates)
        _issue(issues, "error", f"complete-bipartite coverage has duplicate pair(s): {rendered}", page)
    if not missing and not unexpected_internal and not duplicates:
        # This is an informational line represented by a warning-free result;
        # the CLI prints the successful check separately.
        return


def validate_document(
    document: Document,
    pages: Optional[Iterable[Page]] = None,
    complete_bipartite: Optional[list[tuple[str, str]]] = None,
) -> list[Issue]:
    """Run structural and topology checks and return errors/warnings."""

    issues: list[Issue] = []
    selected = list(document.pages if pages is None else pages)
    for page in selected:
        by_id = _check_root_and_ids(page, issues)
        _check_edges(page, by_id, issues)
        for first, second in complete_bipartite or []:
            check_complete_bipartite(page, by_id, first, second, issues)
    return issues


def _normalised_schema_path(document: Document) -> Optional[Path]:
    """Write a schema-friendly uncompressed temporary copy when needed."""

    if document.kind != "mxfile" or not document.has_compressed_pages:
        return None
    root = copy.deepcopy(document.root)
    diagrams = [child for child in root if child.tag.rsplit("}", 1)[-1] == "diagram"]
    for diagram, page in zip(diagrams, document.pages):
        for child in list(diagram):
            diagram.remove(child)
        diagram.text = None
        diagram.append(copy.deepcopy(page.model))
    temporary = tempfile.NamedTemporaryFile(prefix="drawio-validate-", suffix=".drawio", delete=False)
    temporary_path = Path(temporary.name)
    try:
        ET.ElementTree(root).write(temporary, encoding="utf-8", xml_declaration=True)
    finally:
        temporary.close()
    return temporary_path


def run_schema_validation(document: Document, schema: Path) -> tuple[str, Optional[str]]:
    """Run xmllint and return ``(status, detail)``.

    ``status`` is ``ok``, ``error``, or ``warning``.  A temporary uncompressed
    copy is used for compressed pages because the repository schema describes
    the decoded model, not the base64 transport representation.
    """

    xmllint = shutil.which("xmllint")
    if xmllint is None:
        return "warning", "xmllint is unavailable; skipped XSD validation"
    if document.kind != "mxfile":
        return "warning", "input is a bare mxGraphModel; mxfile XSD validation is not applicable"
    if not schema.is_file():
        return "warning", f"schema file is unavailable ({schema}); skipped XSD validation"

    temporary_path = _normalised_schema_path(document)
    input_path = temporary_path or document.path
    if input_path is None:
        return "warning", "document has no source path; skipped XSD validation"
    try:
        result = subprocess.run(
            [xmllint, "--noout", "--schema", str(schema), str(input_path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return "warning", f"could not run xmllint ({exc}); skipped XSD validation"
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except OSError:
                pass

    if result.returncode == 0:
        return "ok", f"XSD validation passed ({schema})"
    detail = (result.stderr or result.stdout or "xmllint returned a nonzero status").strip()
    # Keep command output useful without allowing a malformed embedded label to
    # flood a validation report.
    detail = " | ".join(line.strip() for line in detail.splitlines() if line.strip())
    return "error", f"XSD validation failed: {detail[:2000]}"


def _format_issue(issue: Issue) -> str:
    page = f" [{issue.page.name} / page {issue.page.index + 1}]" if issue.page is not None else ""
    return f"{issue.severity.upper()}{page}: {issue.message}"


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate draw.io XML structure and topology connectivity. Errors return exit status 1; warnings are reported but do not fail the command.",
        epilog=(
            "--complete-bipartite takes two comma-separated vertex-ID lists: "
            "SPINES LEAVES. Example: --complete-bipartite 2,3 9,10,11,12. "
            "Numeric ranges such as 9-12 are accepted. SVG exports are not checked."
        ),
    )
    parser.add_argument("paths", nargs="+", type=Path, metavar="FILE", help="draw.io file(s) to validate")
    parser.add_argument("--page", action="append", metavar="PAGE", help="only validate a 1-based page number, name, or id (repeatable)")
    parser.add_argument(
        "--complete-bipartite",
        action="append",
        nargs=2,
        metavar=("FIRST_IDS", "SECOND_IDS"),
        help="require every pair between the two comma-separated vertex-ID sets (repeatable)",
    )
    schema_group = parser.add_mutually_exclusive_group()
    schema_group.add_argument("--schema", type=Path, metavar="XSD", help=f"validate with this XSD (default: {DEFAULT_SCHEMA})")
    schema_group.add_argument("--no-schema", action="store_true", help="skip optional xmllint/XSD validation")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    schema = None if args.no_schema else (args.schema or DEFAULT_SCHEMA)
    exit_status = 0

    for path in args.paths:
        print(f"File: {path}")
        parse_issues: list[Issue] = []
        try:
            document = load_document(path)
        except DrawioParseError as exc:
            print(f"ERROR: {exc}")
            exit_status = 1
            continue

        selected = select_pages(document, args.page, parse_issues)
        for issue in parse_issues:
            print(_format_issue(issue))
        if any(issue.severity == "error" for issue in parse_issues):
            exit_status = 1
            continue

        complete = [tuple(spec) for spec in (args.complete_bipartite or [])]
        issues = validate_document(document, selected, complete)
        for issue in issues:
            print(_format_issue(issue))
        if not issues:
            print(f"OK: parsed {len(document.pages)} page(s); checked {len(selected)} page(s), {sum(len(page.cells) for page in selected)} cell(s)")

        if complete and not any(issue.severity == "error" and "complete-bipartite" in issue.message for issue in issues):
            for first, second in complete:
                print(f"OK: complete-bipartite coverage checked ({first} x {second})")

        if schema is not None:
            status, detail = run_schema_validation(document, schema)
            if status == "ok":
                print(f"OK: {detail}")
            else:
                print(f"{status.upper()}: {detail}")
            if status == "error":
                exit_status = 1
        if any(issue.severity == "error" for issue in issues):
            exit_status = 1
    return exit_status


if __name__ == "__main__":
    raise SystemExit(main())
