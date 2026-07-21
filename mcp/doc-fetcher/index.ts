#!/usr/bin/env -S npx tsx
// MCP server: pure retrieval of external specs and documentation — IETF RFCs/
// drafts by number/name, general web search to locate a vendor's own docs, and
// arbitrary vendor spec sheets, datasheets, and whitepapers (HTML or PDF) by
// URL, normalized to plain text. No write path: every tool here is a GET,
// nothing here can push config or state anywhere.

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import * as cheerio from "cheerio";
import { compile as compileHtmlToText } from "html-to-text";
import pdfParse from "pdf-parse";
import { z } from "zod";

const RFC_EDITOR_BASE = "https://www.rfc-editor.org/rfc";
const IETF_ARCHIVE_BASE = "https://www.ietf.org/archive/id";
const DATATRACKER_API_BASE = "https://datatracker.ietf.org/api/v1";
const BRAVE_SEARCH_API = "https://api.search.brave.com/res/v1/web/search";
const DUCKDUCKGO_HTML = "https://html.duckduckgo.com/html/";
const FIRECRAWL_SCRAPE_API = "https://api.firecrawl.dev/v1/scrape";
const DEFAULT_MAX_CHARS = 20_000;
const DEFAULT_SEARCH_COUNT = 8;
const MAX_DOWNLOAD_BYTES = 25 * 1024 * 1024; // guard against accidentally fetching huge files

const htmlToText = compileHtmlToText({
  wordwrap: false,
  selectors: [
    { selector: "a", options: { ignoreHref: true } },
    { selector: "img", format: "skip" },
  ],
});

function truncate(text: string, max: number): { text: string; truncated: boolean } {
  if (text.length <= max) return { text, truncated: false };
  return { text: text.slice(0, max), truncated: true };
}

function truncationNote(url: string, max: number): string {
  return `\n\n[... truncated at ${max} characters — fetch ${url} directly for the full text, or raise max_chars ...]`;
}

const server = new McpServer({ name: "doc-fetcher", version: "0.1.0" });

server.tool(
  "fetch_rfc",
  "Fetch the plaintext of an IETF RFC by number from rfc-editor.org. Use this " +
    "whenever a design claim hinges on a specific RFC's normative language " +
    "(MUST/SHOULD/MAY) or section structure, instead of relying on recall.",
  {
    number: z.number().int().positive().describe("RFC number, e.g. 7432 for RFC 7432"),
    max_chars: z
      .number()
      .int()
      .positive()
      .max(100_000)
      .optional()
      .describe("Max characters to return before truncating (default 20000)"),
  },
  async ({ number, max_chars }) => {
    const url = `${RFC_EDITOR_BASE}/rfc${number}.txt`;
    const res = await fetch(url);
    if (!res.ok) {
      return {
        isError: true,
        content: [{ type: "text", text: `Failed to fetch RFC ${number}: HTTP ${res.status} from ${url}` }],
      };
    }
    const body = await res.text();
    const max = max_chars ?? DEFAULT_MAX_CHARS;
    const { text, truncated } = truncate(body, max);
    return {
      content: [{ type: "text", text: truncated ? text + truncationNote(url, max) : text }],
    };
  },
);

server.tool(
  "fetch_draft",
  "Fetch the plaintext of an IETF Internet-Draft from the IETF archive. Requires " +
    "the full draft name including its revision (e.g. draft-ietf-bess-evpn-overlay-12) " +
    "— use search_ietf first if the exact revision isn't known, since drafts (unlike " +
    "RFCs) are revised and old revisions can be superseded or expired.",
  {
    name: z.string().min(1).describe("Full draft name with revision, e.g. draft-ietf-bess-evpn-overlay-12"),
    max_chars: z.number().int().positive().max(100_000).optional(),
  },
  async ({ name, max_chars }) => {
    const draftName = name.endsWith(".txt") ? name.slice(0, -4) : name;
    const url = `${IETF_ARCHIVE_BASE}/${draftName}.txt`;
    const res = await fetch(url);
    if (!res.ok) {
      const base = draftName.replace(/-\d+$/, "");
      return {
        isError: true,
        content: [
          {
            type: "text",
            text:
              `Failed to fetch draft "${name}": HTTP ${res.status} from ${url}. ` +
              `If the revision number is wrong or omitted, check the current revision at ` +
              `https://datatracker.ietf.org/doc/${base}/ or via search_ietf.`,
          },
        ],
      };
    }
    const body = await res.text();
    const max = max_chars ?? DEFAULT_MAX_CHARS;
    const { text, truncated } = truncate(body, max);
    return {
      content: [{ type: "text", text: truncated ? text + truncationNote(url, max) : text }],
    };
  },
);

server.tool(
  "search_ietf",
  "Search the IETF Datatracker for RFCs and Internet-Drafts by name/title keyword. " +
    "Returns name, revision, status, and a datatracker link per match — use this to " +
    "resolve an informal reference (e.g. 'EVPN overlay') to an exact RFC number or " +
    "current draft revision before calling fetch_rfc / fetch_draft.",
  {
    query: z.string().min(1).describe("Keyword to search for, e.g. 'evpn overlay'"),
    limit: z.number().int().positive().max(50).optional().describe("Max results (default 10)"),
  },
  async ({ query, limit }) => {
    const params = new URLSearchParams({
      name__icontains: query.trim().toLowerCase().replace(/\s+/g, "-"),
      format: "json",
      limit: String(limit ?? 10),
    });
    const url = `${DATATRACKER_API_BASE}/doc/document/?${params.toString()}`;
    const res = await fetch(url);
    if (!res.ok) {
      return {
        isError: true,
        content: [{ type: "text", text: `Datatracker search failed: HTTP ${res.status} from ${url}` }],
      };
    }
    const data = (await res.json()) as { objects?: Array<Record<string, unknown>> };
    const objects = data.objects ?? [];
    if (objects.length === 0) {
      return { content: [{ type: "text", text: `No datatracker matches for "${query}".` }] };
    }
    const lines = objects.map((doc) => {
      const name = String(doc.name ?? "?");
      const title = String(doc.title ?? "(no title)");
      const rev = String(doc.rev ?? "?");
      return `- ${name} (rev ${rev}) — ${title} — https://datatracker.ietf.org/doc/${name}/`;
    });
    return { content: [{ type: "text", text: lines.join("\n") }] };
  },
);

interface SearchResult {
  title: string;
  url: string;
  snippet: string;
}

async function searchBrave(query: string, count: number): Promise<SearchResult[]> {
  const params = new URLSearchParams({ q: query, count: String(count) });
  const res = await fetch(`${BRAVE_SEARCH_API}?${params.toString()}`, {
    headers: {
      Accept: "application/json",
      "X-Subscription-Token": process.env.BRAVE_API_KEY as string,
    },
  });
  if (!res.ok) {
    throw new Error(`Brave Search API error: HTTP ${res.status}`);
  }
  const data = (await res.json()) as {
    web?: { results?: Array<{ title: string; url: string; description?: string }> };
  };
  return (data.web?.results ?? []).map((r) => ({
    title: r.title,
    url: r.url,
    snippet: r.description ?? "",
  }));
}

function decodeDuckDuckGoUrl(href: string): string {
  // DDG's HTML results wrap targets as /l/?uddg=<encoded-url>&rut=...
  try {
    const parsed = new URL(href, "https://duckduckgo.com");
    const uddg = parsed.searchParams.get("uddg");
    return uddg ? decodeURIComponent(uddg) : href;
  } catch {
    return href;
  }
}

async function searchDuckDuckGo(query: string, count: number): Promise<SearchResult[]> {
  const params = new URLSearchParams({ q: query });
  const res = await fetch(`${DUCKDUCKGO_HTML}?${params.toString()}`, {
    headers: { "User-Agent": "Mozilla/5.0 (compatible; doc-fetcher/0.1; +https://github.com)" },
  });
  if (!res.ok) {
    throw new Error(`DuckDuckGo search failed: HTTP ${res.status}`);
  }
  const html = await res.text();
  // DDG serves an HTTP 202 "anomaly" challenge page instead of real results when
  // it flags the request (common from datacenter/cloud egress IPs) — treat that
  // as a failure rather than silently reporting "no results".
  if (res.status === 202 || html.toLowerCase().includes("anomaly")) {
    throw new Error(
      "DuckDuckGo returned an anti-bot challenge instead of results (common from " +
        "datacenter/cloud IPs). Set BRAVE_API_KEY in the environment to use the " +
        "Brave Search API instead, which doesn't have this problem.",
    );
  }
  const $ = cheerio.load(html);
  const results: SearchResult[] = [];
  $(".result").each((_, el) => {
    if (results.length >= count) return;
    const titleEl = $(el).find(".result__a").first();
    const title = titleEl.text().trim();
    const href = titleEl.attr("href");
    const snippet = $(el).find(".result__snippet").first().text().trim();
    if (title && href) {
      results.push({ title, url: decodeDuckDuckGoUrl(href), snippet });
    }
  });
  return results;
}

server.tool(
  "search_web",
  "General-purpose web search — use this to locate a vendor's own documentation, " +
    "datasheet, or spec sheet when the exact URL isn't already known (e.g. 'Cisco " +
    "Nexus 9364C-GX datasheet', or 'site:arista.com 7800R4 buffer architecture'). " +
    "Returns title, URL, and snippet per result; feed a result's URL into fetch_doc " +
    "to retrieve and read the actual page or PDF content — this tool only searches, " +
    "it doesn't return full document text. Uses the Brave Search API if BRAVE_API_KEY " +
    "is set in the environment — set it; the no-key DuckDuckGo HTML fallback this " +
    "tool otherwise uses is frequently blocked by an anti-bot challenge from " +
    "server/cloud IPs and will fail outright rather than degrade gracefully when that " +
    "happens.",
  {
    query: z.string().min(1).describe("Search query, e.g. 'Arista 7800R4 datasheet' or 'site:cisco.com Silicon One'"),
    count: z.number().int().positive().max(20).optional().describe("Max results to return (default 8)"),
  },
  async ({ query, count }) => {
    const n = count ?? DEFAULT_SEARCH_COUNT;
    let results: SearchResult[];
    try {
      results = process.env.BRAVE_API_KEY ? await searchBrave(query, n) : await searchDuckDuckGo(query, n);
    } catch (err) {
      return {
        isError: true,
        content: [{ type: "text", text: `Web search failed: ${err instanceof Error ? err.message : String(err)}` }],
      };
    }
    if (results.length === 0) {
      return { content: [{ type: "text", text: `No results for "${query}".` }] };
    }
    const lines = results.slice(0, n).map((r, i) => `${i + 1}. ${r.title}\n   ${r.url}\n   ${r.snippet}`);
    return { content: [{ type: "text", text: lines.join("\n\n") }] };
  },
);

async function scrapeFirecrawl(url: string): Promise<string> {
  const res = await fetch(FIRECRAWL_SCRAPE_API, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${process.env.FIRECRAWL_API_KEY}`,
    },
    body: JSON.stringify({ url, formats: ["markdown"], onlyMainContent: true }),
  });
  if (!res.ok) {
    throw new Error(`Firecrawl scrape failed: HTTP ${res.status}`);
  }
  const data = (await res.json()) as { success?: boolean; data?: { markdown?: string }; error?: string };
  if (!data.success || !data.data?.markdown) {
    throw new Error(`Firecrawl scrape failed: ${data.error ?? "no markdown content returned"}`);
  }
  return data.data.markdown;
}

server.tool(
  "fetch_doc",
  "Fetch an arbitrary document by URL and return its readable plain text — the " +
    "general-purpose retrieval tool for vendor spec sheets, datasheets, whitepapers, " +
    "and other external documentation that (unlike RFCs/drafts) has no standard " +
    "numbered addressing. Handles HTML (converted to readable text, markup stripped) " +
    "and PDF (text-extracted) transparently based on the response's content type; " +
    "any other content type is rejected with the detected type so a different tool " +
    "or approach can be used. This is a plain GET — it cannot authenticate against " +
    "a paywall or portal, so URLs behind a login won't resolve. If FIRECRAWL_API_KEY " +
    "is set in the environment, fetches go through Firecrawl instead of a raw HTTP " +
    "GET — that renders JavaScript first, so it also works on JS-rendered vendor " +
    "pages (common on modern vendor sites) that a raw fetch would return empty.",
  {
    url: z.string().url().describe("Full URL of the document to fetch, e.g. a vendor datasheet PDF or HTML page"),
    max_chars: z
      .number()
      .int()
      .positive()
      .max(100_000)
      .optional()
      .describe("Max characters to return before truncating (default 20000)"),
  },
  async ({ url, max_chars }) => {
    const max = max_chars ?? DEFAULT_MAX_CHARS;

    if (process.env.FIRECRAWL_API_KEY) {
      try {
        const markdown = await scrapeFirecrawl(url);
        const { text, truncated } = truncate(markdown.trim(), max);
        return {
          content: [{ type: "text", text: truncated ? text + truncationNote(url, max) : text }],
        };
      } catch (err) {
        return {
          isError: true,
          content: [{ type: "text", text: err instanceof Error ? err.message : String(err) }],
        };
      }
    }

    let res: Response;
    try {
      res = await fetch(url);
    } catch (err) {
      return {
        isError: true,
        content: [{ type: "text", text: `Failed to fetch ${url}: ${err instanceof Error ? err.message : String(err)}` }],
      };
    }
    if (!res.ok) {
      return {
        isError: true,
        content: [{ type: "text", text: `Failed to fetch ${url}: HTTP ${res.status}` }],
      };
    }

    const contentType = (res.headers.get("content-type") ?? "").toLowerCase();
    const contentLength = Number(res.headers.get("content-length") ?? "0");
    if (contentLength > MAX_DOWNLOAD_BYTES) {
      return {
        isError: true,
        content: [
          {
            type: "text",
            text: `Refusing to fetch ${url}: reported size ${contentLength} bytes exceeds the ${MAX_DOWNLOAD_BYTES}-byte limit for this tool.`,
          },
        ],
      };
    }

    let text: string;
    if (contentType.includes("application/pdf") || url.toLowerCase().endsWith(".pdf")) {
      const buffer = Buffer.from(await res.arrayBuffer());
      const parsed = await pdfParse(buffer);
      text = parsed.text;
    } else if (contentType.includes("text/html")) {
      text = htmlToText(await res.text());
    } else if (contentType.startsWith("text/") || contentType.includes("json") || contentType === "") {
      text = await res.text();
    } else {
      return {
        isError: true,
        content: [
          {
            type: "text",
            text: `Unsupported content type "${contentType}" at ${url}. This tool handles HTML and PDF only.`,
          },
        ],
      };
    }

    const { text: truncatedText, truncated } = truncate(text.trim(), max);
    return {
      content: [{ type: "text", text: truncated ? truncatedText + truncationNote(url, max) : truncatedText }],
    };
  },
);

const transport = new StdioServerTransport();
await server.connect(transport);
// stderr, not stdout — stdout is the JSON-RPC channel to the MCP client and
// any extra text written there would corrupt the protocol stream.
console.error("doc-fetcher MCP server running on stdio");
