# drawio-mcp — Network-Topology Workflow

Entry point for **reading, editing, and creating** network-topology diagrams in
the draw.io format, using the pinned `drawio-mcp` submodule in this directory.
No MCP server and no draw.io Desktop required — the submodule is the static
reference library; the net-architect agent does the authoring.

> Convention: one `<plugin-name>.md` per plugin lives directly in `plugins/`
> (this file documents the `plugins/drawio-mcp` submodule). Future plugins get
> their own `<plugin-name>.md`; do not add another `README.md` here.

Pinned submodule commit: `14b318b19cc37b159f841227b9d11fbd18ce18ea` (drawio-mcp
`main`) [1].

## Where to look (single source of truth)

This file is an index — the authoritative content lives in the submodule and is
**not duplicated here**. Consult the right file before authoring:

| Workflow / task | Consult (in `plugins/drawio-mcp/`) |
|---|---|
| Authoring rules (styles, edges, containers, layers, well-formedness) | `shared/xml-reference.md` — "General principles", "Edges", "Containers and groups", "CRITICAL: XML well-formedness" [2] |
| Minimal valid file template | `shared/style-reference.md` — §1 "File Structure Overview" [3] |
| Style-string syntax & shape list | `shared/style-reference.md` — §2 "Style String Format", §3 "Shape Types", §4 "Style Properties Reference" [3] |
| Mermaid authoring & CLI convert/ELK/export — **draw.io Desktop only**, unavailable in this environment (§3.1, §4) | `shared/mermaid-reference.md` [4]; SKILL.md "The pipeline", "ELK layout for XML", "draw.io CLI" [5] |
| `#create=` browser URL generation | `plugins/claude-code/skills/drawio/SKILL.md` — "Browser URL output" [5] |
| Vendor/industry icon styles | `shape-search/search-index.json` (10,446 shapes) [6] |
| Validation schema | `shared/mxfile.xsd` [7] |

## 1. Reading a topology diagram

The submodule has no read/extract workflow — this part lives here.

### 1.1 `.drawio` files

An `<mxfile>` document with one or more `<diagram>` pages. Each page body is
either plain `mxGraphModel` XML (starts with `<`) or compressed
`base64( deflateRaw( xml ) )` — detect per page, since pages can mix states [8].

```python
import base64, zlib, xml.dom.minidom as md

def load_page(path, page_index=0):
    dom = md.parseString(open(path).read())
    body = dom.getElementsByTagName('diagram')[page_index].firstChild.nodeValue.strip()
    if not body.startswith('<'):
        body = zlib.decompress(base64.b64decode(body), -15).decode()
    return md.parseString(body)
```

### 1.2 `.drawio.svg` exports

The SVG root's `content` attribute holds the HTML-escaped `mxfile` XML [8]:

```python
import html, xml.etree.ElementTree as ET
import xml.dom.minidom as md

svg = ET.parse('diagram.drawio.svg')
model = md.parseString(html.unescape(svg.getroot().attrib['content']))
```

### 1.3 From mxGraphModel to a topology

Cells `id="0"` (root) and `id="1"` (default layer) are structural, not devices.
**Vertices** (`vertex="1"`) = devices; **edges** (`edge="1"`) = links via
`source`/`target`. Extract: collect vertices by ID, edges by endpoint IDs, and
group vertices that share a parent container ID (the grouping boxes). The
`style` attribute identifies device type: `shape=...` for library shapes,
`image=data:image/...` for embedded artwork (e.g. Visio-imported stencils).

Imported (Visio) diagrams additionally carry a `vsdxID=<n>` style key on every
imported cell — an internal provenance marker stamped by draw.io's VSDX import
code (`mxVsdxConstants.VSDX_ID`; the value is the source Visio shape ID, kept
for round-tripping) [9]. VSDX import is available only in the web editor
(app.diagrams.net), so imported files also carry `host="app.diagrams.net"` [10].
The key is not part of the documented XML format; ignore it when reading.

---

## 2. Editing

Apply the rules in `xml-reference.md` "CRITICAL: XML well-formedness" and
"Containers and groups" [2]; style changes follow `style-reference.md` §2 [3].
Validate after every edit:

```bash
xmllint --noout --schema plugins/drawio-mcp/shared/mxfile.xsd file.drawio
```

---

## 3. Creating

1. **Author** — as **XML**. This environment has no draw.io Desktop, so Mermaid
   authoring (which needs the desktop CLI to convert) is out of scope — see
   `mermaid-reference.md` [4] if that changes. Use the template in
   `style-reference.md` §1 [3].
2. **Pick device glyphs** from `shape-search/search-index.json` [6]:

   ```python
   import json
   idx = json.load(open('plugins/drawio-mcp/shape-search/search-index.json'))
   hits = [s for s in idx if 'cisco' in (s.get('style','') or '').lower()
           and 'router' in (s.get('title','') or '').lower()]
   for s in hits[:5]:
       print(s['title'], '|', s['style'][:90])
   ```

   Use the returned `style` verbatim in the `mxCell` style attribute.
3. **Deliver** — write a `*.drawio` file and validate (§2), or generate a
   `#create=` browser URL per SKILL.md "Browser URL output" [5].

**Repo convention**: track the uncompressed `.drawio` file as the canonical
diagram artifact — it is plain XML, so every edit diffs cleanly in git. Keep
the diagram body uncompressed (compressed bodies are base64 blobs whose diffs
are useless). Treat `.drawio.svg` as an on-demand presentation export (§4),
not a tracked file.

---

## 4. Exporting to `.drawio.svg` / images

The MCP tool server has **no export tool**, and draw.io web has no URL
parameter that triggers a file export [11]. A `.drawio.svg` (SVG with the
diagram XML embedded in its `content` attribute) is produced only by draw.io
itself:

- **Web editor**: *File → Export As → SVG* — tick *"Include a copy of my
  diagram"* to embed the XML.
- **Desktop CLI**: `drawio -x -f svg -e -b 10 -o out.drawio.svg in.drawio`
  (the `-e` / `--embed-diagram` flag embeds the XML).

That export runs client-side in the editor (`EditorUi.exportSvg` →
`Graph.getSvg`) and requires the full editor runtime — it cannot be invoked
standalone from a script [12]. Hand-approximating it produces wrong edge
endpoints, since draw.io computes them from the live graph view.

---

## 5. Keeping the submodule updated

```bash
git submodule update --init                        # fresh clone
git submodule update --remote plugins/drawio-mcp   # latest main
```

Pinning to a specific commit is recommended for reproducibility — record the
new SHA in this file's header.

---

## References

[1] jgraph/drawio-mcp repository, pinned at commit `14b318b19cc37b159f841227b9d11fbd18ce18ea` — https://github.com/jgraph/drawio-mcp/tree/14b318b19cc37b159f841227b9d11fbd18ce18ea
[2] drawio-mcp `shared/xml-reference.md` — draw.io XML generation reference — https://github.com/jgraph/drawio-mcp/blob/14b318b19cc37b159f841227b9d11fbd18ce18ea/shared/xml-reference.md
[3] drawio-mcp `shared/style-reference.md` — draw.io style syntax — https://github.com/jgraph/drawio-mcp/blob/14b318b19cc37b159f841227b9d11fbd18ce18ea/shared/style-reference.md
[4] drawio-mcp `shared/mermaid-reference.md` — Mermaid syntax reference — https://github.com/jgraph/drawio-mcp/blob/14b318b19cc37b159f841227b9d11fbd18ce18ea/shared/mermaid-reference.md
[5] drawio-mcp `plugins/claude-code/skills/drawio/SKILL.md` — draw.io diagram skill — https://github.com/jgraph/drawio-mcp/blob/14b318b19cc37b159f841227b9d11fbd18ce18ea/plugins/claude-code/skills/drawio/SKILL.md
[6] drawio-mcp `shape-search/search-index.json` — 10,446 shapes — https://github.com/jgraph/drawio-mcp/blob/14b318b19cc37b159f841227b9d11fbd18ce18ea/shape-search/search-index.json
[7] drawio-mcp `shared/mxfile.xsd` — mxFile XML Schema v1.0 — https://github.com/jgraph/drawio-mcp/blob/14b318b19cc37b159f841227b9d11fbd18ce18ea/shared/mxfile.xsd
[8] drawio-mcp `mcp-tool-server/src/pages.js` — per-page compression handling — https://github.com/jgraph/drawio-mcp/blob/14b318b19cc37b159f841227b9d11fbd18ce18ea/mcp-tool-server/src/pages.js
[9] jgraph/drawio source, `src/main/webapp/js/diagramly/vsdx/importer.js` — `mxVsdxConstants.VSDX_ID = "vsdxID"` (line ~2867), stamped on imported cells via `styleMap[VSDX_ID]` (lines ~11593/13216); module overview in `js/diagramly/vsdx/CLAUDE.md` — https://github.com/jgraph/drawio/blob/d3140c3105c7fe8fb47259f6283e7ef566c647c6/src/main/webapp/js/diagramly/vsdx/importer.js
[10] draw.io manual, "No .vsd file import in the Desktop app" — VSDX import only via the free web application at app.diagrams.net — https://www.drawio.com/docs/manual/import/vsd-import-desktop/
[11] draw.io docs, "Supported URL parameters" — no parameter triggers a file export — https://www.drawio.com/doc/faq/supported-url-parameters
[12] jgraph/drawio source: `src/main/webapp/js/diagramly/EditorUi.js` `EditorUi.prototype.exportSvg` (~line 7858; embeds XML via `svgRoot.setAttribute('content', …)` at ~line 7967) and `src/main/webapp/js/grapheditor/Graph.js` `Graph.prototype.getSvg` (~line 21712) — https://github.com/jgraph/drawio/blob/d3140c3105c7fe8fb47259f6283e7ef566c647c6/src/main/webapp/js/diagramly/EditorUi.js

