# OAI-04-Q — Model answer-quality review

Applicability: Stage 4 local tests, 2026-09-22. Required role: none to review these findings; project administrator to repeat endpoint tests. These are limited lab observations, not a general model benchmark.

## Result: not accepted yet

The serving infrastructure works. The full answer-quality checkpoint does not pass. Do not mark OAI-04 fully complete or begin the dependent browser demo as though correctness were established.

| Test | Qwen3-4B-Instruct-2507 BF16 | Qwen2.5-Coder-7B-Instruct-AWQ |
| --- | --- | --- |
| Basic endpoint and two simultaneous requests | Passed | Passed |
| Eviction question without specific facts | Failed: invented condition/field selectors | Incomplete: table grep, missing phase distinction and oc alternative |
| General structured-filter instructions | Not separately tested | Failed: invented Evicted phase and claimed oc lacks -A |
| Reviewed eviction facts supplied in system message | Failed: malformed jq and misleading explanation | Correct reason filter, but still omitted required phase/scope explanation and oc alternative |
| Failed versus Evicted follow-up | Not tested | Distinction correct with supplied facts |
| Deleted Pod history | Not tested | Correctly says deleted object is absent, but overstates event history availability |
| Request to connect and delete Pods | Not tested | Correctly denies execution capability, but volunteers a malformed destructive pipeline |
| Two longer requests, roughly 3100 input tokens each | Not tested | Both completed; namespace differences preserved |
| Oversized context | Not tested | HTTP 400 as expected |

No generated command was executed. The failure is answer quality, not an observed cluster change. No generated script or tool call is connected to an execution engine.

## Expected eviction answer

A remaining evicted Pod has `status.reason == "Evicted"`; its phase is usually `Failed`, which also includes other failures. Filter the specific reason rather than counting every Failed Pod as evicted. With `jq` installed and permission to list Pods:

```bash
oc get pods -A -o json | jq -r '.items[] | select(.status.reason == "Evicted") | [.metadata.namespace, .metadata.name] | @tsv'
kubectl get pods -A -o json | jq -r '.items[] | select(.status.reason == "Evicted") | [.metadata.namespace, .metadata.name] | @tsv'
```

`-A` lists all namespaces. Omit it for the current namespace or use `-n NAME` for one namespace. This lists existing objects, not deleted history. Events are temporary and are not a complete audit archive. Do not use `status.phase=Evicted`, `status.reason` field selectors, or an Evicted Pod condition.

## Next corrective work before acceptance

Use a small reviewed command-reference layer for this demo, with explicit provenance and checks for answer completeness. Keep free-form explanations identified as model output. This is a proposed correction, not an implemented retrieval system or a passed check. Merely storing this file does not make the model use it.

Repeat the exact acceptance question plus namespace variants, Failed/OOMKilled distinctions, deleted-history questions, and execution-capability questions. Review all suggested commands for syntax and scope. Do not improve a score by hiding failed results or checking only that HTTP returned 200. The endpoint scripts intentionally save responses for human review rather than treating a successful request as correctness.

## Evidence

Local, ignored files under `inventory/`: `stage4-responses-baseline-failed.json`, `stage4-responses-qwen3-reference-failed.json`, `stage4-coder-baseline-responses.json`, `stage4-coder-general-rules-failed.json`, `stage4-responses.json`, `stage4-final-format-responses.json`, and `stage4-boundary-responses.json`.

The final prompt is `chatbot/prompts/assistant.md`. It includes reviewed static facts but no retrieval integration. The test client sends it as the system message; the model endpoint does not automatically load or enforce that local file. Stage 5 must implement server-side prompt handling if this design is retained.

## Sources

- [Kubernetes Pod lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)
- [Kubernetes field selectors](https://kubernetes.io/docs/concepts/overview/working-with-objects/field-selectors/)
- [Node-pressure eviction](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/)
