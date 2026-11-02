# Huawei

Hub for Huawei's product lines. Each line belongs to one network domain; solution
and device detail live in the linked files.

| Domain | Device line | Current software | Legacy (do not reference) | Solution / controller |
|---|---|---|---|---|
| Data center fabric | [CloudEngine (CE series)](cloudengine.md) | V300 (V300R026C00 for the CE9800/8800/6800 and CE16800 families) | V200 | [CloudFabric](cloudfabric.md) with iMaster NCE-Fabric |
| Campus | S-series | V600 (V600R025C10) | V200 | iMaster NCE-Campus |
| WAN | NetEngine (NE series) | — | — | iMaster NCE-IP |
| Storage network | CloudEngine SAN models (box: CE6885-SAN, CE8855H-SAN, CE8865-SAN; chassis: CE16800-X) | Solution V100R025C10 | — | [Xinghe NoF+](nof-plus.md) with OceanStor Dorado |

Version rule: see [SKILL.md](../../../SKILL.md#3-vendors). CloudEngine version
sources are in [cloudengine.md](cloudengine.md#version-line-v300).

Campus and data center product lines run different OS trains — do not conflate
them. V600 on campus S-series is not the same CLI or feature set as V300 on
CloudEngine.

## Documentation sources

support.huawei.com requires login, so a URL cannot verify a Huawei product
documentation fact — the single exception to the URL requirement in
[docs/authoring.md](../../../docs/authoring.md#source-annotations).

**One identifier per audience tier:**

- **After-sales** (Support portal, HedEx product documentation): an `EDOC...` document ID.
- **Pre-sales** (solution design guides, technical presentations): an `itemId`, a
  32-character hex string.

**Precedence — after-sales outranks pre-sales** whenever both cover the same claim:

- Read after-sales first: device product documentation for the version and model, then
  solution deployment guides. It states published behaviour.
- Pre-sales material is written ahead of the product and often not revisited when it
  changes, so cite it only for what it alone can state: solution version history,
  compatibility matrices, positioning and cost comparisons, reference customers, and
  design-level recommendations the product documentation does not carry.
- Never repeat a pre-sales figure that an after-sales document contradicts or narrows.
  Replace it from the after-sales source, or record both and mark which is which — and
  in any file that mixes the tiers, mark the tier per claim.

**Every References entry** records the title, its `EDOC` or `itemId`, product or solution
version, issue number, issue date, the table-of-contents path (or slide number) to the
section, and the date last confirmed. A document or package outside a HedEx library
additionally records where Huawei publishes it: its software release ID, or the package
that contains it.

- **Never invent an identifier.** If an ID, a library, or an origin is missing, ask the
  user for it rather than searching for one, and do not fall back to a local mirror's
  folder name or write "supplied by the user".
- **Verification** is a read of that section in a local copy of the HedEx library. Do not
  fetch or search the web for Huawei documentation.
- **Converting**: a library ships as a single `.hdx` file. Convert it with
  [huawei-hdx-converter.py](https://gist.github.com/chenmicro/3f1008e180af05f7ee45fa739cfa133f)
  (`python3 huawei-hdx-converter.py library.hdx`), which writes a `library_web/`
  folder: topics under `content/`, table of contents in `toc.js`.

## VRP (Versatile Routing Platform)

- Huawei's unified network OS across its routing and switching portfolio —
  broadly analogous in role to Cisco IOS or Juniper Junos: one config
  model/CLI family spanning CloudEngine and NetEngine product lines, which
  simplifies operational training across a mixed Huawei fleet compared to
  vendors that split OS trains by product line.
- VRP's command syntax and structured config model will be unfamiliar to
  Cisco/Juniper-trained operators even though the underlying concepts
  (interfaces, VRFs, routing protocols, ACLs) map directly — factor in
  operator retraining time when a design proposes introducing Huawei gear into
  a previously Cisco/Juniper/Arista-only environment, it's a real but often
  underestimated cost.

## CloudEngine vs. NetEngine

- **CloudEngine (CE series)**: Huawei's data-center switching line. See
  [cloudengine.md](cloudengine.md).
- **NetEngine (NE series)**: Huawei's routing line — WAN edge, service-provider
  core, MPLS/SR — the default choice for
  [techniques/mpls.md](../../techniques/mpls.md) and
  [segment-routing.md](../../techniques/segment-routing.md). Don't conflate the two
  lines by name alone; "NetEngine" routers and "CloudEngine" switches serve
  distinct roles even though both run VRP.

## iMaster NCE

- Huawei's SDN controller / network-cloud-automation platform — spans
  intent-based fabric provisioning, telemetry, and closed-loop automation,
  broadly playing the same role Cisco ACI/APIC or Juniper Apstra play for
  their respective DC fabrics, with additional variants/modules extending into
  campus (NCE-Campus) and WAN (NCE-IP) domains. The data center variant,
  NCE-Fabric, is covered in [cloudfabric.md](cloudfabric.md).
- FabricInsight, the NCE analyzer, is a separate product with its own documentation and
  its own release line. It owns the O&M claims in [nof-plus.md](nof-plus.md): read it for
  what the analyzer reports, and the switch documentation for what the switch measures and
  exports.
- Procurement note relevant to design conversations rather than technical
  ones: Huawei networking equipment is subject to restrictions or outright
  bans in a number of jurisdictions and for certain customer sectors
  (government, critical infrastructure, telecom in several countries) —
  worth flagging early in a vendor-selection conversation rather than
  discovering it after a design is otherwise finalized.
