# net-architect

An agent skill for network **solution design and architecture**, not Day-2 operations.
It works with any AI agent that can read files, and gives it a reference library and
a retrieval tool, so recommendations rest on real product lines and current
specifications. It never touches live infrastructure.

## What it can do

- Design, review, size, and compare data center fabrics (including AI/GPU), campus
  networks, SD-WAN/SASE, and WAN/MPLS/segment routing.
- Evaluate or choose between vendors: Cisco, Arista, Juniper, Huawei, Extreme Networks,
  Cato, IBM, Netis, Dynatrace, and NETSCOUT.
- Pull in an IETF RFC or draft, or a current vendor spec sheet, when the library doesn't
  cover a claim, then save what it learns back into the library.
- Read, edit, and create network topology figures in draw.io format.

## How to use it

1. Clone the repo and open it in your agent.
2. Optional, for live retrieval: register the two MCP servers listed in `.mcp.json`,
   `doc-fetcher` and `fetch`, if your agent supports MCP. `doc-fetcher` needs
   `npm install` first; see the [setup guide](mcp/doc-fetcher/README.md). Without them,
   the agent works from the library alone.
3. Tell the agent to load `SKILL.md`, then ask a design question, for example:
   - "Design a 512-GPU training fabric with RoCEv2."
   - "Compare ACI and NX-OS EVPN-VXLAN for a two-site data center."
   - "Plan a campus refresh that also replaces the MPLS WAN edge."

The agent reads only the files a request touches. New facts are left as uncommitted
edits for you to review.

**Huawei documentation** requires a login, so the agent can't fetch it. Download the
`.hdx` library and convert it with
[huawei-hdx-converter.py](https://gist.github.com/chenmicro/3f1008e180af05f7ee45fa739cfa133f),
then tell the agent where the output is.

## What's in the repo

| Path | Contents |
|---|---|
| [skills/scenarios/](skills/scenarios/) | End-to-end requests: which files to read, and the judgment between them |
| [skills/techniques/](skills/techniques/) | One file per technique, such as VXLAN, EVPN, or BGP |
| [skills/vendor-matrix/](skills/vendor-matrix/) | Vendor platforms, operating systems, and solutions |
| [skills/pocs/](skills/pocs/) | What broke in real tests, and how it was fixed |
| [mcp/doc-fetcher/](mcp/doc-fetcher/) | Retrieval tool for RFCs, drafts, web search, and vendor documents |
| [docs/](docs/) | Authoring, commit, and topology figure rules |

## How to contribute

- Follow [docs/authoring.md](docs/authoring.md) for citations, file placement, and
  splitting, and [docs/git-policy.md](docs/git-policy.md) for commits.
- Keep each technique in one file, and keep scenario files thin: link to techniques
  rather than restating them.
- Prefer concrete, decision-relevant content (thresholds, tradeoffs, when to use what)
  over marketing language or exhaustive feature lists.
- Keep `doc-fetcher` a thin retrieval tool, with no design judgment and no write or
  configuration capability.
- Update the routing tables in `SKILL.md` whenever a file or tool is added, renamed, or
  rescoped.

## License

CC BY-SA 4.0 — see [LICENSE](LICENSE).
