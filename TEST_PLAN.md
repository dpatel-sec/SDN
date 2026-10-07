# Test Plan

Use this checklist to prove that the project is a working SDN implementation and that Zero Trust policy enforcement is active.

## 1. Environment Checks

Run:

```bash
python3 --version
ryu-manager --version
sudo mn --version
sudo ovs-vsctl --version
```

Record the versions in `results and future scope`.

## 2. Controller Startup

Run:

```bash
ryu-manager my_controller.py
```

Expected:

- The controller starts without Python errors.
- The terminal prints that 6 Zero Trust hosts and 20 policy pairs were loaded.

## 3. Topology Startup

Run:

```bash
sudo python3 my_custom_topology.py
```

Inside Mininet:

```bash
nodes
net
dump
```

Expected:

- Hosts `h1` through `h6` exist.
- Switches `s1`, `s2`, and `s3` exist.
- Hosts have deterministic IP and MAC addresses that match `zero_trust_policy.json`.

## 4. Allowed Connectivity

Inside Mininet:

```bash
h1 ping -c 3 h2
h1 ping -c 3 h4
h2 ping -c 3 h4
h3 ping -c 3 h4
h4 ping -c 3 h5
h6 ping -c 3 h5
```

Expected:

- These tests succeed.
- The controller prints `ALLOW` log lines.

## 5. Denied Microsegmentation

Inside Mininet:

```bash
h3 ping -c 3 h5
h1 ping -c 3 h5
h2 ping -c 3 h5
```

Expected:

- These tests fail.
- The controller prints `DENY reason=ipv4-policy-deny` or `DENY reason=arp-policy-deny`.

## 6. Source Spoofing Protection

Inside Mininet:

```bash
h3 ifconfig h3-eth0 10.0.0.5 netmask 255.255.255.0
h3 ping -c 3 h4
```

Expected:

- Traffic is denied.
- The controller prints `DENY reason=source-ip-spoofing`.

Reset h3:

```bash
h3 ifconfig h3-eth0 10.0.0.3 netmask 255.255.255.0
```

## 7. Port Scan Detection

Inside Mininet:

```bash
h3 nmap -p 1-30 10.0.0.4
```

Expected:

- The controller detects repeated probes.
- The controller temporarily blocks h3 after the threshold is crossed.

## 8. Packet-Rate Detection

Inside Mininet:

```bash
h3 ping -f -c 100 10.0.0.4
```

Expected:

- The controller prints a temporary block warning if the packet-rate threshold is exceeded.

## 9. Performance Measurement

Inside Mininet:

```bash
h4 iperf -s &
h1 iperf -c 10.0.0.4 -t 10
```

Expected:

- Throughput is reported by iperf.
- Record the result before and after changing policy thresholds if you are comparing performance trade-offs.

## 10. Cleanup

Inside Mininet:

```bash
exit
```

Then:

```bash
sudo mn -c
```
