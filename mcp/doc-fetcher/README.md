# doc-fetcher setup

`doc-fetcher` is a pure-retrieval MCP server for IETF RFCs and drafts, web search, and
vendor documents. It runs as a local subprocess that your MCP client launches over
stdio. It isn't installed by cloning the repo alone, because it has its own dependencies.

## Install

You need Node.js 18+ and outbound internet access (see [Network access](#network-access)).

```bash
cd mcp/doc-fetcher
npm install
```

Every clone needs its own `npm install`, because `node_modules/` is gitignored.

## Optional API keys

Both keys are optional. `doc-fetcher` works without them, but it's more fragile on
blocked search backends and JavaScript-heavy vendor pages. Set the variable and the tool
switches backend automatically.

| Tool | Without a key | With a key |
|---|---|---|
| `search_web` | Scrapes DuckDuckGo HTML, which is routinely blocked from server, cloud, and CI IPs | `BRAVE_API_KEY` from [brave.com/search/api](https://brave.com/search/api/) (free tier available) |
| `fetch_doc` | Raw GET with HTML and PDF parsing, which returns an empty shell on JavaScript-rendered pages | `FIRECRAWL_API_KEY` from [firecrawl.dev](https://www.firecrawl.dev/) (free tier available, also self-hostable) |

```bash
export BRAVE_API_KEY="your-key-here"
export FIRECRAWL_API_KEY="your-key-here"
```

## Verify

The MCP Inspector lets you call the tools without registering anything:

```bash
npx -y @modelcontextprotocol/inspector npx tsx index.ts
```

Try `fetch_rfc` with `number: 2119`. Getting RFC 2119's text back confirms the server
starts and can reach the internet.

## Register

Any MCP client can run this server. The root `.mcp.json` lists it alongside `fetch`
(`mcp-server-fetch`, which needs `uvx`), and clients that read that file can use it
directly.

For other clients, add this to the client's MCP configuration, keeping the keys you have:

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

For example, in Claude Code, from the repo root:

```bash
claude mcp add doc-fetcher \
  --env BRAVE_API_KEY="$BRAVE_API_KEY" \
  --env FIRECRAWL_API_KEY="$FIRECRAWL_API_KEY" \
  -- npx tsx mcp/doc-fetcher/index.ts
```

## Tools

| Tool | Example arguments | Returns |
|---|---|---|
| `fetch_rfc` | `{ "number": 2119, "max_chars": 300 }` | RFC plaintext, truncated with a note pointing at the full URL |
| `fetch_draft` | `{ "name": "draft-sajassi-drake-l2vpn-evpn-overlay-00" }` | Draft text. Needs the exact revision; call `search_ietf` if you only know the topic |
| `search_ietf` | `{ "query": "evpn overlay", "limit": 3 }` | Matching drafts and RFCs by name, revision, title, and datatracker link |
| `search_web` | `{ "query": "Cisco Nexus 9364C-GX datasheet", "count": 5 }` | Numbered title, URL, and snippet results. Use it to find a URL for `fetch_doc` |
| `fetch_doc` | `{ "url": "https://www.rfc-editor.org/rfc/rfc9000.pdf" }` | Plain text from an HTML or PDF URL. An unsupported type returns an error naming the type |

## Network access

There is no offline mode and no cached copy. Every call is a live HTTPS request, and it
fails outright rather than returning stale data if the host is unreachable.

| Host | Used by |
|---|---|
| `www.rfc-editor.org` | `fetch_rfc` |
| `www.ietf.org` | `fetch_draft` |
| `datatracker.ietf.org` | `search_ietf` |
| `api.search.brave.com` or `html.duckduckgo.com` | `search_web`, with or without `BRAVE_API_KEY` |
| `api.firecrawl.dev` | `fetch_doc` with `FIRECRAWL_API_KEY` |
| The vendor's own domain | `fetch_doc` without a key, so it needs unrestricted HTTPS egress |

Huawei product documentation requires a login, so this tool can't retrieve it.

## Troubleshooting

- **`getaddrinfo ENOTFOUND` or DNS errors on `npm install`**: a transient resolver issue,
  so retry. Check connectivity with
  `curl -sS -o /dev/null -w "%{http_code}\n" https://www.rfc-editor.org/`.
- **`fetch_draft` returns HTTP 404**: the revision is wrong, or the draft was superseded
  or expired. Use `search_ietf` to find the current name.
- **`search_web` reports a DuckDuckGo anti-bot challenge**: expected from datacenter,
  cloud, and CI IPs. Set `BRAVE_API_KEY`; there's no workaround on the DuckDuckGo path.
- **`fetch_doc` misses content you can see in a browser**: the page is client-rendered
  and the raw GET doesn't run JavaScript. Set `FIRECRAWL_API_KEY`.
- **`fetch_doc` returns a PDF parse error**: this happens on malformed test PDFs without
  `FIRECRAWL_API_KEY`. If a vendor PDF fails, it's likely image-only; neither `pdf-parse`
  nor Firecrawl can OCR it.
- **`fetch_doc` returns "Unsupported content type"**: the no-key path handles only HTML
  and PDF. The message names the type it saw, so check the URL.
- **`fetch_doc` returns a Firecrawl error**: this path wasn't tested live when the tool
  was built. Check the message against [Firecrawl's API docs](https://docs.firecrawl.dev/);
  the integration is a plain REST call to `/v1/scrape`.
