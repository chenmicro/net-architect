#!/usr/bin/env python3
"""Assemble the generated MkDocs source tree for GitHub Pages.

The repository remains the canonical source.  This script copies all of
``skills/`` and ``docs/`` into an ignored build directory, makes ``SKILL.md``
the website home page, and replaces draw.io figure links with generated SVG
previews while retaining links to the editable sources.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import unicodedata
from pathlib import Path
from urllib.parse import unquote


DRAWIO_LINK = re.compile(
    r"(?<!!)\[(?P<label>[^\]\n]+)\]\((?P<target>[^)\s]+\.drawio)\)"
)
FIGURE_REFERENCE = re.compile(
    r"\[Figure (?P<number>[0-9]+) — (?P<caption>[^\]\n]+)\]"
    r"\((?P<target>[^)\s]+\.drawio)\)"
)
MARKDOWN_LINK = re.compile(
    r"(?<!!)\[(?P<label>[^\]\n]+)\]\((?P<target>[^)\s]+)\)"
)


class PagesBuildError(RuntimeError):
    """Raised when the publication tree cannot be assembled safely."""


def _rendered_svgs(drawio: Path) -> list[Path]:
    export_dir = drawio.parent / "_figures"
    single_page = export_dir / f"{drawio.stem}.svg"
    if single_page.is_file():
        return [single_page]
    return sorted(export_dir.glob(f"{drawio.stem}-*.svg"))


def _relative_url(path: Path, parent: Path) -> str:
    return Path(os.path.relpath(path, parent)).as_posix()


def _render_figure_reference(match: re.Match[str], markdown: Path, docs_root: Path) -> str:
    label = f"Figure {match.group('number')} — {match.group('caption')}"
    target = match.group("target")
    drawio = (markdown.parent / target).resolve()
    try:
        drawio.relative_to(docs_root.resolve())
    except ValueError as error:
        raise PagesBuildError(
            f"draw.io link in {markdown} escapes the publication tree: {target}"
        ) from error

    exports = _rendered_svgs(drawio)
    if not exports:
        raise PagesBuildError(
            f"no SVG export found for {drawio}; run the draw.io export step first"
        )

    images = []
    for page_number, svg in enumerate(exports, start=1):
        page_label = label if len(exports) == 1 else f"{label} — page {page_number}"
        images.append(f"![{page_label}]({_relative_url(svg, markdown.parent)})")
    images.append(f"[Editable draw.io source]({target})")
    return "\n\n".join(images)


def _inline_code_removed(line: str) -> str:
    return re.sub(r"(`+)(.*?)\1", "", line)


def _rewrite_figure_links(markdown: Path, docs_root: Path) -> int:
    original = markdown.read_text(encoding="utf-8")
    rewritten_lines: list[str] = []
    count = 0
    fence_character: str | None = None
    fence_length = 0

    for line_number, line in enumerate(original.splitlines(keepends=True), start=1):
        body = line.rstrip("\r\n")
        newline = line[len(body):]
        if fence_character is not None:
            closing_fence = re.match(
                rf"^[ ]{{0,3}}{re.escape(fence_character)}{{{fence_length},}}[ \t]*$",
                body,
            )
            if closing_fence:
                fence_character = None
                fence_length = 0
            rewritten_lines.append(line)
            continue

        opening_fence = re.match(r"^[ ]{0,3}(`{3,}|~{3,})", body)
        if opening_fence:
            marker = opening_fence.group(1)
            fence_character = marker[0]
            fence_length = len(marker)
            rewritten_lines.append(line)
            continue

        match = FIGURE_REFERENCE.fullmatch(body)
        if match:
            rendered = _render_figure_reference(match, markdown, docs_root)
            rewritten_lines.append(rendered + newline)
            count += 1
            continue

        if DRAWIO_LINK.search(_inline_code_removed(body)):
            raise PagesBuildError(
                f"invalid draw.io figure reference at {markdown}:{line_number}; "
                "put one '[Figure N — caption](file.drawio)' reference on its own line"
            )
        rewritten_lines.append(line)

    rewritten = "".join(rewritten_lines)
    if rewritten != original:
        markdown.write_text(rewritten, encoding="utf-8")
    return count


def _page_title(markdown: Path) -> str:
    for line in markdown.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return markdown.stem.replace("-", " ").replace("_", " ").title()


def _contains_markdown(directory: Path) -> bool:
    return any(
        path.is_file() and not any(part.startswith("_") for part in path.relative_to(directory).parts)
        for path in directory.rglob("*.md")
    )


def _create_directory_indexes(docs_root: Path) -> int:
    created = 0
    directories = sorted(
        (path for path in docs_root.rglob("*") if path.is_dir()),
        key=lambda path: len(path.parts),
        reverse=True,
    )
    for directory in directories:
        if directory.name.startswith("_") or not _contains_markdown(directory):
            continue
        index = directory / "index.md"
        if index.exists():
            continue
        readme = directory / "README.md"
        if readme.exists():
            readme.replace(index)
            created += 1
            continue

        title = directory.name.replace("-", " ").replace("_", " ").title()
        entries: list[str] = []
        for child in sorted(directory.iterdir(), key=lambda path: path.name.casefold()):
            if child.name.startswith("_"):
                continue
            if child.is_dir() and _contains_markdown(child):
                label = child.name.replace("-", " ").replace("_", " ").title()
                entries.append(f"- [{label}]({child.name}/index.md)")
            elif child.suffix == ".md" and child.name not in {"index.md", "README.md"}:
                entries.append(f"- [{_page_title(child)}]({child.name})")
        index.write_text(f"# {title}\n\n" + "\n".join(entries) + "\n", encoding="utf-8")
        created += 1
    return created


def _source_parent(markdown: Path, docs_root: Path, repository_root: Path) -> Path:
    relative = markdown.relative_to(docs_root)
    if relative.as_posix() in {"index.md", "about.md"}:
        return repository_root
    return repository_root / relative.parent


def _mkdocs_slug(fragment: str) -> str:
    value = unicodedata.normalize("NFKD", unquote(fragment))
    value = value.encode("ascii", "ignore").decode("ascii").lower()
    value = re.sub(r"[^\w\s-]", "", value).strip()
    return re.sub(r"[-\s]+", "-", value)


def _rewrite_local_links(
    markdown: Path,
    docs_root: Path,
    repository_root: Path,
    repository_url: str | None,
) -> int:
    original = markdown.read_text(encoding="utf-8")

    def replacement(match: re.Match[str]) -> str:
        label = match.group("label")
        target = match.group("target")
        if target.startswith(("#", "/", "http://", "https://", "mailto:")):
            return match.group(0)

        path_part, separator, fragment = target.partition("#")
        decoded = unquote(path_part)
        staged_target = (markdown.parent / decoded).resolve()
        try:
            staged_target.relative_to(docs_root.resolve())
        except ValueError:
            return match.group(0)

        suffix = f"#{_mkdocs_slug(fragment)}" if separator else ""
        alias: Path | None = None
        if staged_target == docs_root / "SKILL.md":
            alias = docs_root / "index.md"
        elif staged_target == docs_root / "README.md":
            alias = docs_root / "about.md"
        elif staged_target.name == "README.md" and (staged_target.parent / "index.md").is_file():
            alias = staged_target.parent / "index.md"
        if alias is not None:
            rewritten = _relative_url(alias, markdown.parent) + suffix
            return f"[{label}]({rewritten})"
        if staged_target.is_dir() and (staged_target / "index.md").is_file():
            rewritten = path_part.rstrip("/") + "/index.md" + suffix
            return f"[{label}]({rewritten})"
        if staged_target.exists():
            if separator and suffix != f"#{fragment}":
                return f"[{label}]({path_part}{suffix})"
            return match.group(0)

        source_target = (_source_parent(markdown, docs_root, repository_root) / decoded).resolve()
        try:
            relative_source = source_target.relative_to(repository_root.resolve())
        except ValueError:
            return match.group(0)
        if repository_url and source_target.exists():
            view = "tree" if source_target.is_dir() else "blob"
            external = f"{repository_url.rstrip('/')}/{view}/main/{relative_source.as_posix()}{suffix}"
            return f"[{label}]({external})"
        return match.group(0)

    rewritten, count = MARKDOWN_LINK.subn(replacement, original)
    if rewritten != original:
        markdown.write_text(rewritten, encoding="utf-8")
    return count


def assemble(
    repository_root: Path,
    build_root: Path,
    repository_url: str | None = None,
) -> tuple[int, int, int]:
    repository_root = repository_root.resolve()
    build_root = build_root.resolve()
    if build_root.parent != repository_root or build_root.name != ".pages-build":
        raise PagesBuildError(
            "the build directory must be <repository>/.pages-build"
        )

    required = [repository_root / "SKILL.md", repository_root / "README.md"]
    required.extend(repository_root / name for name in ("skills", "docs"))
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise PagesBuildError(f"required publication source is missing: {', '.join(missing)}")

    if build_root.exists():
        shutil.rmtree(build_root)
    docs_root = build_root / "docs"
    docs_root.mkdir(parents=True)

    shutil.copy2(repository_root / "SKILL.md", docs_root / "index.md")
    shutil.copy2(repository_root / "README.md", docs_root / "about.md")
    shutil.copytree(repository_root / "skills", docs_root / "skills")
    shutil.copytree(repository_root / "docs", docs_root / "docs")

    drawio_files = sorted(docs_root.rglob("*.drawio"))
    missing_exports = [str(path) for path in drawio_files if not _rendered_svgs(path)]
    if missing_exports:
        rendered = "\n  - ".join(missing_exports)
        raise PagesBuildError(f"missing SVG export(s):\n  - {rendered}")

    directory_indexes = _create_directory_indexes(docs_root)
    rewritten_figures = sum(
        _rewrite_figure_links(markdown, docs_root)
        for markdown in sorted(docs_root.rglob("*.md"))
    )
    for markdown in sorted(docs_root.rglob("*.md")):
        _rewrite_local_links(
            markdown,
            docs_root,
            repository_root,
            repository_url,
        )
    return len(drawio_files), rewritten_figures, directory_indexes


def parse_args() -> argparse.Namespace:
    repository_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository-root",
        type=Path,
        default=repository_root,
        help="repository root (defaults to the parent of tools/)",
    )
    parser.add_argument(
        "--build-root",
        type=Path,
        default=repository_root / ".pages-build",
        help="must resolve to <repository>/.pages-build",
    )
    parser.add_argument(
        "--repository-url",
        help="public repository URL used for source files outside skills/ and docs/",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        diagrams, links, indexes = assemble(
            args.repository_root,
            args.build_root,
            args.repository_url,
        )
    except (OSError, PagesBuildError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(
        f"assembled {args.build_root / 'docs'}: "
        f"{diagrams} diagram(s), {links} published figure link(s), "
        f"{indexes} generated directory index(es)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
