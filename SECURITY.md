# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in qStack, please report it responsibly:

- **Email:** security@qstack.dev (or open a [Private security advisory](https://github.com/mindevis/qStack/security/advisories/new))
- **Response time:** Within 48 hours
- **Disclosure:** We will acknowledge and fix the issue before public disclosure

### What to include

- Type of vulnerability (RCE, XSS, SQLi, Auth bypass, Privilege escalation, etc.)
- Affected service/component (qstack-api, qstack-compute, agent, etc.)
- Steps to reproduce
- Impact assessment (if known)

### What NOT to do

- Do not disclose the vulnerability publicly until we have released a fix
- Do not exploit the vulnerability beyond what is necessary for proof-of-concept

### Scope

The following components are in scope:

- API Gateway (`qstack-api`) — Auth, JWT, Rate limiting
- Compute service (`qstack-compute`) — VM lifecycle, Live migration
- Agent (`qstack-agent`) — Hypervisor access, Heartbeat
- Storage/Network services — Volume/Network configuration
- gRPC mTLS communication between services
- OpenBao/Vault secrets management
- Talos Linux deployment scripts

### Out of scope

- Third-party services (NATS, PostgreSQL, Libvirt) — report to their maintainers
- Social engineering / Phishing
- Denial of Service on infrastructure providers (EKS/GKE/AKS)

## Security Features

| Feature | Status | Description |
|---------|--------|-------------|
| **mTLS** | Implemented | All gRPC communication uses mutual TLS |
| **JWT Auth** | Implemented | API Gateway with token rotation |
| **Secrets Management** | Implemented | OpenBao/Vault for credentials at rest |
| **PCI-DSS** | Planned | Admin/User dashboard compliance |
| **Vulnerability Scanning** | Planned | Image scanning pipeline |
| **Audit Logging** | Planned | All API actions logged |
