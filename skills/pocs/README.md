# POC Records

Operational knowledge captured from real cross-vendor POC tests. Each file
documents what was tested, what broke, and how it was resolved — the type of
knowledge that architecture docs miss.

## Convention

- **One file per POC engagement** — named `YYYY-MM-short-description.md`
- Each file records: test topology, config snippets as tested (including broken versions), symptoms, root cause, fix, and what to verify before repeating
- POC records are **not** scenarios — they don't prescribe architecture. They're the git-blame of real testing

## Index

| File | Integration pattern | Vendors involved | Key issues encountered |
|---|---|---|---|
| [2026-07-cisco-huawei-dci-firewall.md](2026-07-cisco-huawei-dci-firewall.md) | Huawei CE M-LAG ↔ Cisco FW BGP peering (service insertion) | Huawei CloudFabric, Cisco ASA/FTD | BGP over M-LAG: FW pointed at individual CE IP, not shared anycast IP; EVPN→BGP route redistribution missing; sub-int VLAN mismatch; FW TCP normalization dropping BGP SYN; MTU fragmentation across service chain; BGP→EVPN Type-5 reverse path missing | |
