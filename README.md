# net-architect

A Claude skill package for network **solution design and architecture** work (not
Day-2 operations): data center fabrics, campus networks, SD-WAN/SASE, and WAN/MPLS —
plus a vendor matrix (Cisco, Arista, Juniper, Huawei) so recommendations stay grounded
in real product lines instead of generic claims, and a pure-retrieval MCP tool
(Node/TypeScript throughout, matching the web-heavy nature of the retrieval work) for
the part static knowledge can't cover: general web search, and pulling an actual IETF
RFC/draft or a current vendor spec sheet into context.

## Structure

- **[SKILL.md](SKILL.md)** — entry point and routing table: when to load which
  scenario/technique/vendor file and when to reach for `doc-fetcher`. Load this first.
- **[skills/scenarios/](skills/scenarios/)** — cross-technique composition guidance for
  specific end-to-end asks (e.g. an AI/GPU training cluster buildout, or a campus
  refresh that also touches the WAN edge): which technique/vendor files to read, in
  what order, and the judgment that only exists at the intersection between them.
- **[skills/techniques/](skills/techniques/)** — flat, atomic technique library, one
  file per technique (VXLAN, EVPN, BGP, NAC, SASE, ...) with no domain grouping in
  between; a technique used by more than one scenario, or by another technique file,
  is still written exactly once.
- **[skills/vendor-matrix/](skills/vendor-matrix/)** — vendor-specific platform, OS,
  and silicon notes (Cisco, Arista, Juniper, Huawei).
- **[mcp/doc-fetcher/](mcp/doc-fetcher/)** — pure-retrieval MCP server (Node/
  TypeScript) for IETF RFCs/drafts, general web search, and vendor spec
  sheets/whitepapers.

## Design intent

The `skills/` tree is meant to be read selectively, not loaded wholesale. `SKILL.md`
carries a routing table so an agent (or a human skimming the repo) can pull in only the
scenario, technique, and vendor files a given request actually touches, and treat the
rest as available-but-unread. The tree is split into two layers, deliberately without a
domain grouping in between: `techniques/` (and `vendor-matrix/`) are the reusable,
write-once library — one technique like EVPN or 802.1X gets exactly one file, even
though it's used across many kinds of requests, and a technique that another technique
depends on (e.g. EVPN and the DC underlay both riding on BGP) links to that file rather
than re-explaining it; `scenarios/` composes them for specific end-to-end asks (which
is what actually represents a solution) without duplicating any of that technique
content. `doc-fetcher` is the escape hatch for anything that isn't stable
enough to write down — current RFC/draft status, or current-generation vendor specs —
so the `skills/` files can stay purely about design judgment rather than growing stale
copies of things that change on their own. This package is scoped to a Network Solution
Specialist/Architect persona: it brings external specs and documentation into context,
and deliberately stops there — it has no tool that reaches into live infrastructure.

## Tutorial: setting up `doc-fetcher`

`doc-fetcher` is an independent package with its own dependencies — it's not installed
by cloning this repo alone, and it isn't a hosted service; it runs as a local
subprocess that your MCP client (Claude Code, another MCP-aware client) launches on
demand over stdio.

### 1. Prerequisites

- Node.js 18+ (`node --version`)
- Outbound internet access — see [Network access](#network-access) below

### 2. Install dependencies

```bash
cd mcp/doc-fetcher
npm install
```

This pulls down `@modelcontextprotocol/sdk`, `zod`, `html-to-text`, `pdf-parse`, and
`cheerio` into a local `node_modules/` (gitignored — every clone needs its own
`npm install`).

### 3. (Recommended) Set up optional premium backends

Two tools have a free, zero-setup path and an optional paid-API path that's more
reliable — both follow the same pattern: set the env var, and the tool switches
backend automatically, no code or flag needed.

- **`search_web`** — without setup, falls back to scraping DuckDuckGo's HTML
  search, which works fine from a residential connection but is routinely blocked
  by an anti-bot challenge from server/cloud/CI IPs (confirmed while building this
  tool, not hypothetical) — when that happens the call fails outright with a
  message pointing back here, rather than silently returning nothing. Get a free
  key at [brave.com/search/api](https://brave.com/search/api/) (free tier covers
  casual use):

  ```bash
  export BRAVE_API_KEY="your-key-here"
  ```

- **`fetch_doc`** — without setup, does a raw HTTP GET and parses HTML/PDF itself
  (`cheerio` + `pdf-parse`), which returns an empty/broken result on JavaScript-
  rendered pages (common on modern vendor sites built with React/Next.js — the
  raw HTML is just an empty shell). Get a key at
  [firecrawl.dev](https://www.firecrawl.dev/) (free tier available; the open-source
  engine is also self-hostable) and fetches will render JS first:

  ```bash
  export FIRECRAWL_API_KEY="your-key-here"
  ```

Both are optional — `doc-fetcher` is fully functional with neither set, just more
fragile on adversarial search backends and JS-heavy vendor pages.

### 4. Verify it works

The fastest way to exercise all the tools interactively, without registering
anything yet, is the official MCP Inspector:

```bash
npx -y @modelcontextprotocol/inspector npx tsx index.ts
```

This opens a local web UI that lists the server's tools and lets you call them with
real arguments and see the raw response. Try `fetch_rfc` with `number: 2119` — you
should get back RFC 2119's actual text (the "MUST/SHOULD/MAY" RFC), confirming both
that the server starts cleanly and that it can reach the internet.

### 5. Register it with your MCP client

For Claude Code, from the repo root — pass the optional keys via `--env` so they
reach the server subprocess regardless of what's exported in your interactive shell:

```bash
claude mcp add doc-fetcher \
  --env BRAVE_API_KEY="$BRAVE_API_KEY" \
  --env FIRECRAWL_API_KEY="$FIRECRAWL_API_KEY" \
  -- npx tsx mcp/doc-fetcher/index.ts
```

(Adjust the path if you're registering it from somewhere other than the repo root —
`claude mcp add` accepts an absolute path too. Drop either `--env` flag you don't
have a key for; both are optional, per step 3.) Confirm it's registered:

```bash
claude mcp list
```

Alternatively, add it directly to a `.mcp.json` (project-scoped) or your client's
global MCP config:

```json
{
  "mcpServers": {
    "doc-fetcher": {
      "command": "npx",
      "args": ["tsx", "index.ts"],
      "cwd": "/absolute/path/to/net-architect/mcp/doc-fetcher",
      "env": {
        "BRAVE_API_KEY": "your-key-here",
        "FIRECRAWL_API_KEY": "your-key-here"
      }
    }
  }
}
```

### 6. What each tool looks like in use

- **`fetch_rfc`** — `{ "number": 2119, "max_chars": 300 }` returns RFC 2119's
  plaintext starting from its header, truncated at 300 characters with a note
  pointing at the full URL if you need more.
- **`fetch_draft`** — `{ "name": "draft-sajassi-drake-l2vpn-evpn-overlay-00" }`
  requires the exact revision; if you only know the topic, call `search_ietf` first.
- **`search_ietf`** — `{ "query": "evpn overlay", "limit": 3 }` returns matching
  drafts/RFCs by name, revision, title, and a datatracker link, e.g.
  `draft-sajassi-drake-l2vpn-evpn-overlay (rev 00) — A Network Virtualization
  Overlay Solution using E-VPN`.
- **`search_web`** — `{ "query": "Cisco Nexus 9364C-GX datasheet", "count": 5 }`
  returns numbered title/URL/snippet results (via Brave if `BRAVE_API_KEY` is set,
  otherwise DuckDuckGo) — use this to find the URL, then pass it to `fetch_doc` to
  actually read the page.
- **`fetch_doc`** — `{ "url": "https://www.rfc-editor.org/rfc/rfc9000.pdf" }`
  works against arbitrary HTML or PDF URLs (vendor datasheets, spec sheets,
  whitepapers), returning extracted plain text either way. An unsupported content
  type (e.g. an image) comes back as a clear error naming the detected type rather
  than garbage output. Routes through Firecrawl if `FIRECRAWL_API_KEY` is set.

### Network access

`doc-fetcher` has no offline mode and no bundled/cached copies of anything — every
tool call is a live outbound HTTPS request, by design, so answers reflect what's
published right now rather than a snapshot frozen at whatever point this repo was
last updated. It needs outbound internet access to:

- `www.rfc-editor.org` — RFC plaintext (`fetch_rfc`)
- `www.ietf.org` — Internet-Draft archive (`fetch_draft`)
- `datatracker.ietf.org` — IETF document search API (`search_ietf`)
- `api.search.brave.com` (`search_web`, if `BRAVE_API_KEY` is set) or
  `html.duckduckgo.com` (`search_web`, fallback with no key)
- `api.firecrawl.dev` (`fetch_doc`, if `FIRECRAWL_API_KEY` is set) — otherwise
  `fetch_doc` hits whatever vendor domain the URL points at directly (Cisco,
  Arista, Juniper, Huawei, or any other public spec sheet/datasheet/whitepaper host)

If the environment running the MCP server process sits behind a firewall or an
egress allowlist, these hosts (or, for `fetch_doc`, unrestricted HTTPS egress) need
to be reachable or the corresponding tool calls will fail outright rather than
degrade to stale data.

### Troubleshooting

- **`getaddrinfo ENOTFOUND` / DNS errors on `npm install`** — transient resolver
  hiccup, not a code issue; retry. Confirm general connectivity first with something
  like `curl -sS -o /dev/null -w "%{http_code}\n" https://www.rfc-editor.org/`.
- **`fetch_draft` returns HTTP 404** — the revision number in the draft name is
  wrong or the draft has been superseded/expired. Run `search_ietf` to find the
  current name/revision rather than guessing.
- **`search_web` fails with "DuckDuckGo returned an anti-bot challenge"** — this is
  expected, not a bug: DuckDuckGo's HTML search routinely 202-challenges requests
  from datacenter/cloud/CI IPs (confirmed while building this tool — it's not
  hypothetical). Set `BRAVE_API_KEY` (see step 3 above); there's no workaround on
  the DuckDuckGo path itself.
- **`fetch_doc` returns HTML that's missing the content you can see in a browser**
  — without `FIRECRAWL_API_KEY` set, `fetch_doc` does a raw GET and never executes
  JavaScript, so a client-rendered vendor page can come back as an empty shell.
  Set `FIRECRAWL_API_KEY` (see step 3 above) so fetches render JS first.
- **`fetch_doc` on a PDF returns a parse error** (e.g. `bad XRef entry`) instead of
  text — this happens on a handful of malformed or intentionally-nonstandard test
  PDFs when running without `FIRECRAWL_API_KEY`; real-world vendor datasheets and
  RFC PDFs (e.g. `https://www.rfc-editor.org/rfc/rfc9000.pdf`) parse cleanly with
  the `pdf-parse` fallback. If a specific vendor PDF fails, it's likely
  scanned-image-only (no embedded text layer) — neither `pdf-parse` nor Firecrawl
  can OCR, so there's nothing to extract.
- **`fetch_doc` returns "Unsupported content type"** — only applies to the no-key
  fallback path, which only handles HTML and PDF; the message names the actual
  content type it saw (image, video, etc.) so you can tell whether the URL was even
  the right one.
- **`fetch_doc` fails with a Firecrawl error message** — this path (used when
  `FIRECRAWL_API_KEY` is set) wasn't verified live while building this tool, unlike
  everything else here — no Firecrawl account was available to test against. If it
  errors, check the message against
  [Firecrawl's API docs](https://docs.firecrawl.dev/) first; the integration is a
  plain REST call to their `/v1/scrape` endpoint, nothing more.

## Contributing

- Keep each `skills/techniques/` file scoped to exactly one technique, matching its
  `SKILL.md` table row — split into a new file rather than overload an existing one
  when a second, distinct technique creeps in.
- Keep `skills/scenarios/` files thin: composition and cross-cutting judgment only,
  linking directly into `skills/techniques/` files rather than restating them — a
  technique used by multiple scenarios (or referenced by another technique file)
  must stay written once.
- Prefer concrete, decision-relevant content (thresholds, tradeoffs, when-to-use-what)
  over marketing language or exhaustive feature lists.
- Keep `doc-fetcher` a thin, pure-retrieval tool — fetch and normalize to text only, no
  design judgment and no write/config capability, ever.
- Update `SKILL.md`'s routing tables whenever a file or tool is added, renamed, or
  rescoped.

## License

CC BY-SA 4.0 — see [LICENSE](LICENSE).
