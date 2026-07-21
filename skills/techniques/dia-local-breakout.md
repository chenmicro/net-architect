# DIA (Direct Internet Access) / Local Breakout

- DIA lets branch sites break out to the internet locally (for SaaS, general web
  traffic) instead of backhauling everything through a DC/hub for centralized
  internet egress — this is one of SD-WAN's headline benefits over legacy
  MPLS-only WANs, since it removes the DC as a bottleneck and latency detour for
  cloud-destined traffic.
- The tradeoff is security posture: local breakout means branch-level traffic isn't
  passing through a centralized firewall/inspection stack, so DIA designs need
  either local security stack at the branch (NGFW/UTM on the edge device) or a
  cloud-delivered security layer in the breakout path — this is exactly where
  [sase.md](sase.md) convergence fits in.
- Not all traffic should take DIA — the policy should classify traffic (by app,
  destination, or category) and selectively steer: trusted SaaS (O365, known cloud
  apps) direct, everything else backhauled or security-inspected. "All traffic DIA"
  and "no traffic DIA" are both usually wrong; the design work is in the
  classification and steering policy.
