# Engineering Practice Guide: Sandbox Execution and WORM Logging

## Purpose

- Provide system-level enforcement guidance for secure code execution and immutable auditing.
- Translate design abstractions (ToolGateway, Envelope, DonePredicate) into enforceable runtime controls.

## Secure Sandbox Execution

### Capability Boundaries

- Allowed: call whitelisted tools via runtime wrappers, read/write `/workspace`, pure computation.
- Disallowed: network access, external command execution, reading host paths, privilege escalation.

### Isolation Controls

- Network: `none` (no interfaces).
- File system: read-only root; writable volume only at `/workspace`.
- Capabilities: `cap_drop=["ALL"]`.
- User: non-privileged (e.g., `nobody`).
- Resource limits: strict CPU/memory/time constraints.
- Image hygiene: minimal base image; remove `curl/wget/nc`, `requests/urllib/socket` libraries.

### Seccomp Profile (JSON Sketch)

```json
{
  "defaultAction": "SCMP_ACT_ERRNO",
  "architectures": ["SCMP_ARCH_X86_64"],
  "syscalls": [
    {"names": ["read", "write", "close", "fstat", "lseek"], "action": "SCMP_ACT_ALLOW"},
    {"names": ["mmap", "mprotect", "munmap", "brk"], "action": "SCMP_ACT_ALLOW"},
    {"names": ["rt_sigaction", "rt_sigprocmask"], "action": "SCMP_ACT_ALLOW"},
    {"names": ["access", "openat", "newfstatat"], "action": "SCMP_ACT_ALLOW"},
    {"names": ["getpid", "getuid", "getgid"], "action": "SCMP_ACT_ALLOW"},
    {"names": ["exit", "exit_group"], "action": "SCMP_ACT_ALLOW"},
    {"names": ["futex", "clock_gettime"], "action": "SCMP_ACT_ALLOW"}
  ]
}
```

### Auditing

- Log tool calls, parameters (sanitized), results, durations, and step invariants.
- Include input/output hashes and stagnation detections in the Event Log.

## WORM Logging Practices

- API: append-only Event Log; indices are append-only.
- Batch sealing: append dedicated sealing events with merkle root and signature.
- Export: implement `export(run_id)` for external audit recomputation.

## Envelope and DonePredicate in Practice

- Envelope: enforce capability whitelist, risk level, and budget limits at the ToolGateway + SecurityBoundary.
- DonePredicate: require evidence conditions and invariant checks before step completion.
- Stagnation detection: terminate iterative steps if progress halts within budget.

## Verification Playbook

- Pen-test sandbox: attempt sockets, external exec, reading `/etc/passwd` → blocked by isolation.
- Image scan: confirm absence of risky binaries/libraries.
- Audit replay: recompute Hash Chain and merkle roots from exported events; verify signatures.

## Implementation Tips

- Declarative policy: describe Envelope and tool capabilities in machine-readable contracts.
- Observability: integrate tracing/metrics hooks to monitor gate decisions and loop progress.
- Fail-closed: deny on ambiguity; require explicit approvals for high-risk envelopes.

## Source References

- Architecture (authoritative): [Architecture.md](../design/Architecture.md)
- Interfaces (authoritative): [Interfaces.md](../design/Interfaces.md)
- Architecture (archived): [Architecture_Final_Review_v2.1.md](../design/archive/Architecture_Final_Review_v2.1.md)
- Loop model (Envelope/DonePredicate): [Agent_Framework_Loop_Model_v2.2_Final.md](../design/archive/Agent_Framework_Loop_Model_v2.2_Final.md)
- Industrial-grade security details (sandbox, WORM closures): [Industrial_Agent_Framework_v2.4_Verifiable_Closures.md](../design/archive/Industrial_Agent_Framework_v2.4_Verifiable_Closures.md)
