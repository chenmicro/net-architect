# NAC (Network Access Control)

- **802.1X** is the standard for authenticated, encrypted-key wired/wireless port
  access — supplicant (endpoint) ↔ authenticator (switch/AP) ↔ authentication server
  (RADIUS, e.g. Cisco ISE, Aruba ClearPass). Use it wherever the endpoint can run a
  supplicant (managed laptops, corporate devices).
- **MAB** (MAC Authentication Bypass) is the fallback for devices that can't do
  802.1X (printers, older IoT, badge readers) — authenticates by MAC address against
  a known-device list. Weaker assurance than 802.1X (MACs are spoofable), so MAB
  ports/VLANs should get the same segmentation/least-privilege treatment, not a pass.
- **Dynamic VLAN assignment via RADIUS**: the authentication server returns a VLAN
  (or, more granularly, a security group tag) as part of the RADIUS Access-Accept,
  so a single physical port can serve different roles per authenticated identity
  instead of static per-port VLAN configuration. This is what makes hoteling/BYOD
  campus designs tractable.
- **SGT/TrustSec-style tagging** (Cisco's implementation; other vendors have
  equivalents) decouples policy from IP addressing and VLAN topology — endpoints get
  tagged at authentication and policy enforcement (firewall/switch ACL) is expressed
  in terms of tags, not subnets. This matters for designs where segmentation needs
  to survive IP renumbering or span L3 boundaries without a matching VLAN everywhere.
- Design failure mode to flag: NAC deployed without a tested fail-open/fail-closed
  and monitor-mode rollout plan tends to lock out legitimate devices on cutover.
  Recommend a monitor (audit-only) phase before enforcement in any brownfield rollout.
