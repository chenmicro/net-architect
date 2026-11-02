# POC Records

Operational knowledge presented in POC format, from real testing or product
documentation. See [docs/poc-format.md](../../docs/poc-format.md) for the format.

## Index

| File | Integration pattern | Vendors involved | Key issues encountered |
|---|---|---|---|
| [2026-07-cisco-huawei-dci-firewall.md](2026-07-cisco-huawei-dci-firewall.md) | Huawei CE M-LAG ↔ Cisco FW BGP peering (service insertion) | Huawei CloudFabric, Cisco ASA/FTD | BGP over M-LAG: FW peered with the shared IP, not each member M-LAG IP; EVPN→BGP route redistribution missing; FW TCP normalization dropping BGP SYN; BGP→EVPN Type-5 reverse path missing |
| [2026-08-aci-l2-stretch-mstp-native-epg.md](2026-08-aci-l2-stretch-mstp-native-epg.md) | ACI L2 stretch to external SDN: shared IP subnet across two independent MSTP domains isolated via four EPGs + Flood in Encapsulation | Cisco ACI (Nexus 9300-EX), external SDN GW (MSTP) | Single native-VLAN EPG merges MSTP domains; untagged BPDUs silently dropped without native-VLAN EPG; cross-VLAN BUM leakage without Flood in Encapsulation; BPDU Guard on uplink err-disables legitimate link |
| [2026-11-storage-service-port-split-mlag.md](2026-11-storage-service-port-split-mlag.md) | Storage planes plus M-LAG service access on one CE6885-SAN leaf pair, iNOF enabled and zone isolation off | Huawei CloudEngine | A storage port drifting into the M-LAG Eth-Trunk; storage VLAN on the peer-link; DSCP stripped by the untrusted default; headroom pool shared with service ports on one chip; zones treated as isolation when they only classify; a service-side error-down surfacing as a storage notification; reflectors out of sync; iNOF control channel blocked by port, password, or management-address mistakes |
