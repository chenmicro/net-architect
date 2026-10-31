# Authoring the library

Read this before editing anything under `skills/`. It covers how facts are cited,
where they go, and when a file may be created or split.

## Source annotations

Every fact pulled from an external source must carry an IEEE-style numbered citation
in square brackets at the point of use — e.g., `[1]`, `[2]` — with a corresponding
`## References` section at the end of the file listing the full source details in
order of first appearance. Never delete or renumber an existing citation; new sources
get the next available number.

Sources fall into two categories with different handling:

- **Non-changeable** (RFCs, IEEE standards, published journal/conference papers):
  the fact is permanently fixed. Write the relevant detail inline in the technique
  file — a normative requirement, a protocol field definition, a well-known
  constant — so future readers don't need to re-fetch the source. The References
  entry should include the full bibliographic citation plus a URL when available.
  Example: an RFC's normative timer default goes inline; the reference cites the
  RFC number, title, and rfc-editor.org link.

- **Changeable / time-sensitive** (vendor datasheets, product documentation,
  third-party blog/review, vendor compatibility matrix): the fact can go stale
  — a port count, a buffer size, a supported software version, a pricing tier.
  The References entry must record **how to verify** the fact: which vendor
  document, section or chapter name, URL pattern (or search terms), and a
  date/version stamp of when the fact was last confirmed. Prefer the most stable
  URL path available (product-family doc hub over a per-release PDF). Do not
  embed a changeable fact inline as permanent truth without the verification
  path — a stale fact is worse than no fact because it looks authoritative but
  misleads.

Huawei product documentation requires login, so a URL cannot verify it. Cite the
HedEx library title, product version, issue number, issue date, table-of-contents
path, and last-confirmed date instead.

## Agent and user documentation

The root `README.md` is for users only. Do not reference it from `SKILL.md`. Anything
an agent needs belongs in `SKILL.md` or a file it routes to.

## Creating files

Never create a new technique, scenario, or vendor file, or add a table row, while a
question is still open or uncertain. Confirm with the user both that the issue is
resolved and that it's genuinely network architecture/design related.

## Techniques

- Fetched knowledge goes into the matching technique file, not left in chat context.
- **One file per technique** — protocol architecture, vendor-specific implementation
  differences, interop constraints, and cross-vendor defaults mismatches all live in
  the same technique file. Splitting per-protocol vendor behavior across technique
  and vendor files is the wrong cut: a solution architect researching a multi-vendor
  interconnection consults the technique file first and expects the complete answer
  there, not a cross-reference trail to multiple vendor files.
- If a file grows to cover a second distinct technique, split it. If new material
  doesn't fit any existing file, add one plus a row in `SKILL.md`.
- A technique used across many scenarios (e.g. BGP) stays written once, in its own
  file, with everything else linking to it.

### Standard chapter layout

Every technique file should follow a consistent section structure so the content is
navigable and grep-friendly:

```
# [Technique Name]
[Overview — what it does, why it matters in design conversations]
## [Concept section(s)] — as needed per technique
## Cross-vendor / variants
[Vendor implementation comparison table or prose, proprietary vs. open, interop constraints]
## Design considerations
[Decision points, common pitfalls, default behaviors]
## Relationship to other techniques
[Cross-links to related technique files with one-line notes on how they interact]
## References
[Numbered citations, IEEE-style, ordered by first appearance]
```

Not every file needs every section (a protocol with no vendor variants skips
Cross-vendor), but heading names must match exactly across files for searchability.

Before editing any file under `skills/techniques/`, confirm the file contains the four
mandatory `## ` headings from this layout, named exactly — no synonyms, no rewording.
A file may have additional `## ` concept sections above them. If any is missing or
renamed, fix it.

## Vendors

- **Splitting**: when a vendor's coverage spans genuinely distinct, non-interoperable
  solutions (e.g. Cisco ACI vs. NX-OS-native EVPN-VXLAN), create a subfolder with a
  hub file (`cisco/cisco.md`) and one file per solution. Only split when a real
  second solution is confirmed — don't pre-create subfolders. The objective test: if
  the vendor ships a feature under its own separately-versioned Configuration/Solution
  Guide, it gets its own file here.
- **Version scope**: a fact confirmed only against a legacy-version doc is
  **unverified** until confirmed against the current version's documentation or a
  live CLI. Per-product-line version details (which version is current, which is EOL)
  live in the vendor file's version section, never duplicated in `SKILL.md`.

## Scenarios

Don't pre-create scenario files. Add a scenario only after a real cross-technique
request has been confirmed solved and confirmed network-related (double-check with the
user). Keep scenario files thin — composition plus cross-cutting judgment, never a copy
of technique content.
