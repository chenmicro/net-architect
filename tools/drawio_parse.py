#!/usr/bin/env python3
"""Read draw.io files and print a small, topology-oriented report.

The draw.io format stores each page as either an ``mxGraphModel`` element or a
base64 encoded raw-deflate stream containing that element.  This module keeps
that detail out of callers: :func:`load_document` returns the same model for
plain, compressed, and bare ``mxGraphModel`` input.

The module intentionally uses only the Python standard library.  It is also
usable as a command-line report generator::

    python tools/drawio_parse.py topology.drawio
    python tools/drawio_parse.py --format json topology.drawio
"""

from __future__ import annotations

import argparse
import base64
import binascii
import html
import json
import re
import sys
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional
from urllib.parse import unquote
import xml.etree.ElementTree as ET


class DrawioParseError(ValueError):
    """Raised when a draw.io file or page cannot be decoded as XML."""


def _local_name(tag: str) -> str:
    """Return an XML tag name without an optional namespace prefix."""

    return tag.rsplit("}", 1)[-1]


def _as_number(value: Optional[str]) -> Any:
    """Convert a numeric XML attribute for reports while retaining odd text."""

    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return value
    if number.is_integer():
        return int(number)
    return number


class _LabelParser:
    """Turn the small HTML dialect used by draw.io labels into plain text."""

    def __init__(self) -> None:
        self.parts: list[str] = []

    def feed(self, value: str) -> str:
        # A full HTMLParser is unnecessary here and can treat malformed labels
        # as document markup.  Draw.io labels are normally a short, valid HTML
        # fragment, so this deliberately conservative conversion is clearer.
        value = html.unescape(value)
        value = re.sub(r"<\s*(?:br|/p|/div|/li)\s*/?\s*>", "\n", value, flags=re.I)
        value = re.sub(r"<[^>]*>", "", value)
        value = html.unescape(value)
        lines = [re.sub(r"[ \t\r\f\v]+", " ", line).strip() for line in value.split("\n")]
        return "\n".join(line for line in lines if line)


def label_text(value: Optional[str]) -> Optional[str]:
    """Return a readable label from a raw ``mxCell value`` attribute."""

    if value is None:
        return None
    return _LabelParser().feed(value)


def parse_style(style: Optional[str]) -> dict[str, Optional[str]]:
    """Parse a draw.io semicolon-separated style string.

    A style may begin with a bare shape name (for example ``ellipse``) and may
    also contain bare flags such as ``image``.  Bare tokens are represented by
    ``None`` rather than being discarded.
    """

    result: dict[str, Optional[str]] = {}
    if not style:
        return result
    for token in style.split(";"):
        token = token.strip()
        if not token:
            continue
        if "=" in token:
            key, value = token.split("=", 1)
            result[key] = value
        else:
            result[token] = None
    return result


@dataclass
class Point:
    attrs: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "as": self.attrs.get("as") or None,
            "x": _as_number(self.attrs.get("x")),
            "y": _as_number(self.attrs.get("y")),
            "attributes": dict(self.attrs),
        }


@dataclass
class Geometry:
    attrs: dict[str, str]
    points: list[Point] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "x": _as_number(self.attrs.get("x")),
            "y": _as_number(self.attrs.get("y")),
            "width": _as_number(self.attrs.get("width")),
            "height": _as_number(self.attrs.get("height")),
            "relative": _as_number(self.attrs.get("relative")),
            "as": self.attrs.get("as") or None,
            "attributes": dict(self.attrs),
            "points": [point.to_dict() for point in self.points],
        }
        return result


@dataclass
class Cell:
    id: Optional[str]
    value: Optional[str]
    style: str
    parent: Optional[str]
    vertex: bool
    edge: bool
    source: Optional[str]
    target: Optional[str]
    geometry: Optional[Geometry]
    wrapper: Optional[str] = None
    children: list[str] = field(default_factory=list)

    @property
    def label(self) -> Optional[str]:
        return label_text(self.value)

    @property
    def style_properties(self) -> dict[str, Optional[str]]:
        return parse_style(self.style)

    @property
    def is_container(self) -> bool:
        props = self.style_properties
        # Structural cells 0/1 have children too, but they are the root/layer,
        # not user-authored containers.  A draw.io group/container is a vertex
        # with children (or an explicit container/swimlane style).
        return self.vertex and (
            bool(self.children)
            or props.get("container") in {"1", "true"}
            or "swimlane" in props
            or props.get("shape") == "swimlane"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "value": self.value,
            "label": self.label,
            "style": self.style,
            "styleProperties": self.style_properties,
            "parent": self.parent,
            "children": list(self.children),
            "container": self.is_container,
            "vertex": self.vertex,
            "edge": self.edge,
            "source": self.source,
            "target": self.target,
            "geometry": self.geometry.to_dict() if self.geometry else None,
            "wrapper": self.wrapper,
        }


@dataclass
class Page:
    index: int
    id: Optional[str]
    name: str
    compressed: bool
    model: ET.Element
    cells: list[Cell]

    @property
    def graph_attributes(self) -> dict[str, str]:
        return dict(self.model.attrib)

    @property
    def cell_map(self) -> dict[str, Cell]:
        # A duplicate ID is intentionally retained in ``cells`` so the
        # validator can report it; this convenience map is for valid models.
        return {cell.id: cell for cell in self.cells if cell.id is not None}

    @property
    def vertices(self) -> list[Cell]:
        return [cell for cell in self.cells if cell.vertex]

    @property
    def edges(self) -> list[Cell]:
        return [cell for cell in self.cells if cell.edge]

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "id": self.id,
            "name": self.name,
            "compressed": self.compressed,
            "graphAttributes": self.graph_attributes,
            "cellCount": len(self.cells),
            "vertexCount": len(self.vertices),
            "edgeCount": len(self.edges),
            "containers": [cell.id for cell in self.cells if cell.is_container],
            "cells": [cell.to_dict() for cell in self.cells],
        }


@dataclass
class Document:
    path: Optional[Path]
    kind: str
    root: ET.Element
    pages: list[Page]

    @property
    def has_compressed_pages(self) -> bool:
        return any(page.compressed for page in self.pages)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path) if self.path is not None else None,
            "kind": self.kind,
            "pageCount": len(self.pages),
            "pages": [page.to_dict() for page in self.pages],
        }


def _decode_compressed_page(body: str) -> str:
    compact = "".join(body.split())
    if not compact:
        raise DrawioParseError("diagram page is empty")
    try:
        encoded = base64.b64decode(compact, validate=True)
    except (binascii.Error, ValueError):
        try:
            encoded = base64.urlsafe_b64decode(compact + "=" * (-len(compact) % 4))
        except (binascii.Error, ValueError) as exc:
            raise DrawioParseError(f"diagram page is not valid base64: {exc}") from exc

    last_error: Optional[Exception] = None
    for window_bits in (-15, 15, 31):
        try:
            decoded = zlib.decompress(encoded, window_bits).decode("utf-8")
            # Native draw.io compression normally deflates
            # encodeURIComponent(mxGraphModel). Some producers instead
            # deflate the XML directly, so accept both representations.
            if not decoded.lstrip().startswith("<"):
                unquoted = unquote(decoded)
                if unquoted.lstrip().startswith("<"):
                    decoded = unquoted
            return decoded
        except (zlib.error, UnicodeDecodeError) as exc:
            last_error = exc
    raise DrawioParseError(f"diagram page is not valid compressed XML: {last_error}")


def _parse_xml(text: str, description: str) -> ET.Element:
    try:
        return ET.fromstring(text)
    except ET.ParseError as exc:
        raise DrawioParseError(f"{description} is not well-formed XML: {exc}") from exc


def _model_from_diagram(diagram: ET.Element) -> tuple[ET.Element, bool]:
    children = [child for child in diagram if _local_name(child.tag) == "mxGraphModel"]
    if children:
        return children[0], False
    body = (diagram.text or "").strip()
    if not body:
        raise DrawioParseError("diagram page has neither an mxGraphModel nor encoded content")
    if body.startswith("<"):
        model = _parse_xml(body, "diagram page")
        if _local_name(model.tag) != "mxGraphModel":
            raise DrawioParseError(f"diagram page XML root is {_local_name(model.tag)!r}, expected 'mxGraphModel'")
        return model, False
    model = _parse_xml(_decode_compressed_page(body), "decompressed diagram page")
    if _local_name(model.tag) != "mxGraphModel":
        raise DrawioParseError(f"decompressed page root is {_local_name(model.tag)!r}, expected 'mxGraphModel'")
    return model, True


def _first_geometry(cell_element: ET.Element) -> Optional[ET.Element]:
    for child in cell_element.iter():
        if child is not cell_element and _local_name(child.tag) == "mxGeometry":
            return child
    return None


def _geometry_from_element(element: Optional[ET.Element]) -> Optional[Geometry]:
    if element is None:
        return None
    points = [Point(dict(point.attrib)) for point in element.iter() if _local_name(point.tag) == "mxPoint"]
    return Geometry(dict(element.attrib), points)


def _extract_cells(model: ET.Element) -> list[Cell]:
    graph_root = next((child for child in model if _local_name(child.tag) == "root"), None)
    if graph_root is None:
        raise DrawioParseError("mxGraphModel has no root element")

    cells: list[Cell] = []
    # ElementTree has no parent pointers.  The wrapper map is easy to derive by
    # walking the immediate children of root, which is also where top-level
    # cells are defined by the draw.io format.
    wrapper_by_cell: dict[int, ET.Element] = {}
    for wrapper in graph_root:
        if _local_name(wrapper.tag) in {"UserObject", "object"}:
            for nested in wrapper.iter():
                if _local_name(nested.tag) == "mxCell":
                    wrapper_by_cell[id(nested)] = wrapper

    for element in graph_root.iter():
        if _local_name(element.tag) != "mxCell":
            continue
        wrapper = wrapper_by_cell.get(id(element))
        cell_id = element.attrib.get("id") or (wrapper.attrib.get("id") if wrapper is not None else None)
        value = element.attrib.get("value")
        if wrapper is not None:
            # The wrapper's label/value replaces the nested mxCell value when
            # present, matching draw.io's UserObject semantics.
            value = wrapper.attrib.get("label", wrapper.attrib.get("value", value))
        cells.append(
            Cell(
                id=cell_id,
                value=value,
                style=element.attrib.get("style", ""),
                parent=element.attrib.get("parent") or (wrapper.attrib.get("parent") if wrapper is not None else None),
                vertex=element.attrib.get("vertex") == "1",
                edge=element.attrib.get("edge") == "1",
                source=element.attrib.get("source"),
                target=element.attrib.get("target"),
                geometry=_geometry_from_element(_first_geometry(element)),
                wrapper=wrapper.attrib.get("id") if wrapper is not None else None,
            )
        )

    by_id: dict[str, Cell] = {}
    for cell in cells:
        if cell.id is not None and cell.id not in by_id:
            by_id[cell.id] = cell
    for cell in cells:
        if cell.parent in by_id and cell.id is not None:
            by_id[cell.parent].children.append(cell.id)
    return cells


def _document_from_root(root: ET.Element, path: Optional[Path]) -> Document:
    root_name = _local_name(root.tag)
    if root_name == "mxGraphModel":
        model = root
        page = Page(0, None, "Page-1", False, model, _extract_cells(model))
        return Document(path, "mxGraphModel", root, [page])
    if root_name != "mxfile":
        raise DrawioParseError(f"document root is {root_name!r}, expected 'mxfile' or 'mxGraphModel'")
    diagrams = [child for child in root if _local_name(child.tag) == "diagram"]
    if not diagrams:
        raise DrawioParseError("mxfile contains no diagram pages")
    pages: list[Page] = []
    for index, diagram in enumerate(diagrams):
        model, compressed = _model_from_diagram(diagram)
        name = diagram.attrib.get("name") or f"Page-{index + 1}"
        pages.append(Page(index, diagram.attrib.get("id"), name, compressed, model, _extract_cells(model)))
    return Document(path, "mxfile", root, pages)


def load_document(path: str | Path) -> Document:
    """Load a draw.io document from *path*.

    ``path`` may point to a normal ``mxfile`` or directly to a bare
    ``mxGraphModel``.  A :class:`DrawioParseError` is raised for malformed XML,
    unsupported page content, or an absent model root.
    """

    source = Path(path)
    try:
        text = source.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise DrawioParseError(f"cannot read {source}: {exc}") from exc
    root = _parse_xml(text, str(source))
    return _document_from_root(root, source)


def _page_sort_key(cell: Cell) -> tuple[float, float, str]:
    geometry = cell.geometry.to_dict() if cell.geometry else {}
    x = geometry.get("x")
    y = geometry.get("y")
    return (float(y) if isinstance(y, (int, float)) else float("inf"), float(x) if isinstance(x, (int, float)) else float("inf"), cell.id or "")


def _style_excerpt(style: str, limit: int = 180) -> str:
    if len(style) <= limit:
        return style
    return style[: limit - 3] + "..."


def text_report(document: Document, pages: Optional[Iterable[Page]] = None) -> str:
    """Render a concise human-readable report for a parsed document."""

    selected = list(document.pages if pages is None else pages)
    lines = [f"File: {document.path or '<memory>'} ({document.kind})", f"Pages: {len(document.pages)}"]
    for page in selected:
        lines.append(
            f"\nPage {page.index + 1}: {page.name!r}"
            f" (id={page.id or '-'}, {'compressed' if page.compressed else 'uncompressed'})"
        )
        lines.append(f"  Cells: {len(page.cells)} | vertices: {len(page.vertices)} | edges: {len(page.edges)}")
        containers = [cell for cell in page.cells if cell.is_container]
        if containers:
            lines.append("  Containers:")
            for cell in sorted(containers, key=_page_sort_key):
                lines.append(f"    {cell.id or '<missing>'}: label={cell.label!r} parent={cell.parent or '-'} children={len(cell.children)}")
        lines.append("  Vertices:")
        for cell in sorted(page.vertices, key=_page_sort_key):
            geometry = cell.geometry.to_dict() if cell.geometry else {}
            coords = "x={x} y={y} w={width} h={height}".format(
                x=geometry.get("x", "-"), y=geometry.get("y", "-"), width=geometry.get("width", "-"), height=geometry.get("height", "-")
            )
            lines.append(f"    {cell.id or '<missing>'}: label={cell.label!r} parent={cell.parent or '-'} {coords} style={_style_excerpt(cell.style)!r}")
        lines.append("  Edges:")
        for cell in sorted(page.edges, key=lambda item: item.id or ""):
            point_names = []
            if cell.geometry:
                point_names = [point.attrs.get("as", "waypoint") for point in cell.geometry.points]
            lines.append(
                f"    {cell.id or '<missing>'}: {cell.source or '<none>'} -> {cell.target or '<none>'}"
                f" parent={cell.parent or '-'} geometry={'yes' if cell.geometry else 'no'}"
                f" points={','.join(point_names) or '-'} style={_style_excerpt(cell.style)!r}"
            )
    return "\n".join(lines)


def _select_pages(document: Document, selectors: Optional[list[str]]) -> list[Page]:
    if not selectors:
        return list(document.pages)
    pages: list[Page] = []
    for selector in selectors:
        try:
            number = int(selector)
        except ValueError:
            matches = [page for page in document.pages if selector in {page.name, page.id}]
        else:
            matches = [document.pages[number - 1]] if 1 <= number <= len(document.pages) else []
        if not matches:
            raise DrawioParseError(f"page selector {selector!r} did not match a page")
        for page in matches:
            if page not in pages:
                pages.append(page)
    return pages


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Parse draw.io .drawio files and report pages, vertices, edges, labels, geometry, styles, and parent/container relationships.",
        epilog="Pages may be uncompressed XML or base64/raw-deflate XML; bare mxGraphModel input is also accepted.",
    )
    parser.add_argument("paths", nargs="+", type=Path, metavar="FILE", help="draw.io file(s) to inspect")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="report format (default: text)")
    parser.add_argument("--page", action="append", metavar="PAGE", help="only report a 1-based page number, name, or id (repeatable)")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    reports: list[dict[str, Any]] = []
    text_reports: list[str] = []
    for path in args.paths:
        try:
            document = load_document(path)
            pages = _select_pages(document, args.page)
        except DrawioParseError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        if args.format == "json":
            result = document.to_dict()
            result["pages"] = [page.to_dict() for page in pages]
            result["pageCount"] = len(pages)
            reports.append(result)
        else:
            text_reports.append(text_report(document, pages))
    if args.format == "json":
        output: Any = reports[0] if len(reports) == 1 else {"files": reports}
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print("\n\n".join(text_reports))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
