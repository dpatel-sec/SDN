# Zero Trust SDN with Ryu and Mininet

This project demonstrates a working Software-Defined Networking environment with Zero Trust policy enforcement. It uses Mininet to emulate a small enterprise-style network, Open vSwitch for OpenFlow forwarding, and a Ryu controller to enforce identity checks, microsegmentation, monitoring, and basic attack response.

The original academic goal was to show how centralized SDN control can support Zero Trust Architecture by removing implicit trust from east-west network traffic. The current implementation now includes runnable code and documentation for that goal.

## Project Contents

| File | Purpose |
| --- | --- |
| `my_controller.py` | Ryu OpenFlow 1.3 controller with host identity validation, policy enforcement, deny logging, and temporary blocking for suspicious traffic. |
| `my_custom_topology.py` | Mininet topology with 3 OpenFlow switches and 6 deterministic hosts. |
| `zero_trust_policy.json` | Host inventory, allowed communication pairs, and detection thresholds. |
| `how to run` | Step-by-step setup and demo commands. |
| `TEST_PLAN.md` | Connectivity, microsegmentation, spoofing, scan, and performance tests. |
| `results and future scope` | Results template and future improvements. |
| `requirements.txt` | Python dependencies for the Ryu controller. |
| `SECURITY.md` | Project-specific security policy. |
| `*.pdf` | Original research, thesis/report notes, and Ryu installation notes. |

## Network Design

The topology has one core switch, two access switches, and six hosts.

| Host | IP | MAC | Role | Access port |
| --- | --- | --- | --- | --- |
| h1 | `10.0.0.1` | `00:00:00:00:00:01` | Employee | `s2-eth2` |
| h2 | `10.0.0.2` | `00:00:00:00:00:02` | Employee | `s2-eth3` |
| h3 | `10.0.0.3` | `00:00:00:00:00:03` | Guest | `s2-eth4` |
| h4 | `10.0.0.4` | `00:00:00:00:00:04` | Web service | `s3-eth2` |
| h5 | `10.0.0.5` | `00:00:00:00:00:05` | Database | `s3-eth3` |
| h6 | `10.0.0.6` | `00:00:00:00:00:06` | Monitoring host | `s3-eth4` |

## Zero Trust Controls

- Known-host enforcement: packets from MAC addresses outside the inventory are denied.
- Source validation: each host must use its assigned MAC and IP address.
- Location validation: a host is expected on its assigned access switch port; spoofing from another host-facing access port is treated as suspicious.
- Microsegmentation: only pairs listed in `zero_trust_policy.json` are allowed.
- Default deny: unknown destinations, unsupported Ethernet types, and disallowed pairs are dropped.
- Attack response: packet-rate and port-scan thresholds temporarily block suspicious hosts.
- Controller logging: allowed and denied events are logged by Ryu for audit evidence.

## Expected Demo Behavior

Allowed examples:

```bash
h1 ping -c 3 h2
h1 ping -c 3 h4
h3 ping -c 3 h4
h4 ping -c 3 h5
h6 ping -c 3 h5
```

Denied examples:

```bash
h3 ping -c 3 h5
h1 ping -c 3 h5
h2 ping -c 3 h5
```

The denied tests should show failed connectivity in Mininet and `DENY` events in the Ryu controller terminal.

## Quick Start

Open two terminals in this project directory.

Terminal 1:

```bash
ryu-manager my_controller.py
```

Terminal 2:

```bash
sudo python3 my_custom_topology.py
```

Inside the Mininet CLI:

```bash
h1 ping -c 3 h4
h3 ping -c 3 h5
```

See `how to run` and `TEST_PLAN.md` for the full test procedure.

## Notes

This is a controlled academic demonstration. The authentication model uses deterministic Mininet identities rather than real certificates, MFA, or production NAC integration. The future-scope section lists the improvements needed for a production-grade Zero Trust SDN system.
