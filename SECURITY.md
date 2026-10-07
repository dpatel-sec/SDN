# Security Policy

## Scope

This repository is an academic Zero Trust SDN demonstration using Ryu, Mininet, and OpenFlow. It is not a production security appliance.

Security-sensitive project files include:

- `my_controller.py`
- `my_custom_topology.py`
- `zero_trust_policy.json`
- `requirements.txt`

## Supported Version

The supported version is the current `main` branch of this repository.

## Threat Model

The demo focuses on:

- Unauthorized host communication.
- Unknown host identities.
- Source IP spoofing inside the Mininet topology.
- Basic port-scan behavior.
- Basic high-rate packet behavior.

The demo does not fully protect against:

- Compromised controller hosts.
- Malicious root users inside the Mininet VM.
- Real certificate, MFA, or enterprise identity attacks.
- Production-scale DDoS attacks.
- OpenFlow channel compromise without TLS.

## Reporting Issues

For academic or project use, document issues with:

1. The command that reproduced the issue.
2. The expected behavior.
3. The actual behavior.
4. Controller logs showing `ALLOW`, `DENY`, or traceback output.
5. Any changes made to `zero_trust_policy.json`.

## Secure Demo Recommendations

- Run the project inside a local VM, not on a production network.
- Keep Mininet and Open vSwitch isolated from real interfaces unless you intentionally bridge them.
- Review `zero_trust_policy.json` before demonstrations.
- Do not treat MAC/IP validation as production-grade authentication.
- Use TLS, certificate-based identity, and external policy management for any real deployment.
