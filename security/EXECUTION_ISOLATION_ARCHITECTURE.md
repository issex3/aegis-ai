# Execution isolation architecture

| | |
|---|---|
| Status | DRAFT — design record, not a deployed control |
| Date | 3 November 2026 |

Aegis AI does **not** currently execute customer-supplied code. Assessments send prompts to a customer HTTPS endpoint, or to the built-in demo adapter, and evaluate the observable reply plus any tool calls against an in-memory synthetic sandbox.

This document records what is implemented in the application today, why that is not a substitute for a production execution plane, and what must be built in infrastructure before the product can claim isolated execution.

## Current behaviour (verified in code)

- Agent HTTP calls are made from the API process when `CELERY_BROKER_URL` is empty, or from a Celery worker that uses the **same image, same environment variables, same database credentials, and same encryption key**.
- Outbound calls are restricted in application code: HTTPS only, port 443, public addresses, no redirects, DNS pinned at connect time, response size cap, request size cap.
- Sandbox tools mutate a deep copy of fictional records inside the process. Nothing is written to the host filesystem for sandbox state.
- Per-organisation and global concurrency limits refuse additional assessment jobs (`max_concurrent_assessments_per_org`, `max_concurrent_assessments_global`).
- Assessment duration is bounded in the runner and the scenario engine.

These controls reduce accidental SSRF and resource exhaustion. They are **not** microVM isolation, they are **not** a deny-by-default network, and they do **not** prevent a vulnerability in the HTTP client or JSON parser from executing with control-plane privileges.

## What must not be claimed

- Do not describe the current sandbox as a secure execution environment.
- Do not describe in-process Python tool functions as MicroVMs, gVisor, or Firecracker.
- Do not introduce a Docker socket, privileged containers, or host-network mode to “complete” this requirement.

## Production architecture (required before any customer-code execution)

If Aegis ever runs customer-provided tools, model weights, or untrusted interpreters, the following is mandatory:

1. **Separate execution plane.** Worker pool in its own VPC or project, no route to the control-plane database except through a narrowly scoped job API.
2. **Ephemeral MicroVMs** (Firecracker or an equivalent). One assessment, one VM, destroyed afterwards. No Docker socket.
3. **Deny-by-default egress** via an allowlisting proxy. Explicit destinations only. Block `169.254.169.254`, link-local, RFC1918, and cloud metadata names at the network layer, not only in Python.
4. **No persistent secrets in the VM.** Decrypt the agent credential in the control plane, inject a short-lived copy into the VM for the run, wipe on teardown.
5. **cgroup limits** for CPU, RAM, pids, and disk. Hard wall-clock timeout with hypervisor-level kill.
6. **IMDS disabled** on execution hosts.
7. **Logging** of VM create/destroy, egress denials, and timeouts to the security log stream.

Until that infrastructure exists, keep execution limited to outbound HTTPS to customer endpoints plus in-memory synthetic tools, and treat SEC-015 as an outstanding infrastructure risk.
