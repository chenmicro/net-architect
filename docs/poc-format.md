# POC record format

Read this before creating or editing a POC record under `skills/pocs/`. Records use
POC format to present operational knowledge, from real testing or from product
documentation. Either way, a record shows how a pattern is tested, what can go wrong,
and how to resolve it — the type of knowledge that architecture docs miss.

## Convention

- **One file per scope** — each record has its own scope, stated in Background, and is
  named `YYYY-MM-short-description.md`
- **Source is stated at the top** — a record not tested in a lab starts with a note
  saying so, for example `> Based on product documentation, not lab-tested.`
- **Corrections are marked** — when a real environment shows something is wrong, update
  the content and note it inline, for example `Corrected from live testing, 2026-11`.
  Remove customer names, real addresses, serial numbers, and credentials first
- Issues predicted from documentation carry a citation, like any other external fact
- **Values come from the recommended ranges** — take VLANs, VNIs, bridge domains, and
  interconnection values from the vendor solution guide's recommended or example ranges,
  and flag any value outside them or one the platform reserves
- POC records are **not** scenarios — they don't prescribe architecture
- Add each new record to the [POC index](../skills/pocs/README.md)

## Format

```markdown
# POC: <title>

> Based on product documentation, not lab-tested.

## Background
Why this matters and what the record covers: scope, product versions, and the linked
scenario, if any.

## Test environment
### Topology
### Device list      Role, vendor, model, software version
### Network plan

## Test cases
### TC-01: <test item>
**Objective**:
**Prerequisites**:
**Procedure**:
**Expected result**:
**If it fails**:

## Issues encountered
### ISSUE-01: <short description>
**Found in**: TC-01
**Symptom**:
**Root cause**:
**Fix**:
**Verification**:

## Conclusion

## References
```

Leave a field blank if there is no content for it. Don't fill it with guesses.
