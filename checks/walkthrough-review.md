# Walkthrough review — 2026-09-23

Scope: guide, current source, Kustomize rendering, project permissions, and bounded live API checks on the existing reference lab. No reinstall, model reload, GPU repartitioning, data deletion, or GitOps synchronization was performed. Synced sources were not modified.

This is a historical review before teardown. The reference project and platform resources were subsequently removed. Later read-only inspection found authentication Degraded=False. Use release-review.md for publication status.

## Outcome

The existing model and chat demo work. The walkthrough is now consistent about stage boundaries, current limits, tested results, and incomplete work. It is not yet a fully healthy, independently replayed customer installation: authentication health and broad model-answer quality remain open.

## Corrections

| Finding | Correction |
| --- | --- |
| Stage 4's overlay also deployed the Stage 5 UI | Added deploy/overlays/lab-model; combined lab overlay composes it with chatbot. Rendered combined manifests compare byte-for-byte equal before/after. |
| README and acceptance mixed historical pending statements with completed work | Rewrote current status; kept historical evidence in local notes/inventory; separated serving acceptance from answer-quality acceptance. |
| Memory/support summary used only original 4K limits | Documented current 16K/2048 limits and later 831 MiB sampled headroom. |
| Second GPU described as untested/available | Linked the separate image-generator validation; warned that both GPUs are allocated and new GPU test Jobs will wait. No chat relocation claim. |
| Permission checker lacked an explicit context option and exec/port-forward coverage | Added API target guard, --context, and relevant subresource checks; passed using actual ai-user credentials without switching active context. |
| GitOps/retrieval/H100 modules absent | Added scoped modules and explicit-placeholder Application template; actual adoption/extensions remain untested. |
| No repeatable structural check | Added checks/review-walkthrough.py for Kustomize roots, Python/shell syntax, and local guide links. |

## Current live results

- Observed OpenShift 4.22.13 and OpenShift AI operator 3.5.1. NVIDIA/NFD/AI CSVs Succeeded; GPU ClusterPolicy ready; DataScienceCluster Ready and all requested AI deployment replicas available.
- All five nodes Ready; master/worker machine configuration pools Updated with no degradation; each GPU worker reports one allocatable whole GPU.
- command-helper and image-generator InferenceServices Ready; chatbot and both predictors have all containers Ready and zero restarts at inspection. Both model claims Bound.
- All 37 Kustomize roots rendered; Python/shell syntax and local guide-link checks passed.
- Model-only and combined application overlays passed server dry run using the existing ai-user context. Both renders contain the expected project scope; combined output unchanged by restructuring.
- Actual ai-user permission test passed and checked cluster powers remained denied. Existing credentials worked; this is not a fresh login test.
- Chat API regression passed reviewed reference completeness, input-role/origin/length checks, and two simultaneous model calls.
- Public model API rejected anonymous access (401) and accepted the current authenticated login for model listing and completion (200). This review's Route call used lab-admin; original ai-user Route evidence is recorded separately.
- Chatbot and model-container API token paths remain absent. The platform proxy's separate token exception remains documented.
- GPU computation, storage relocation, browser interactions, and long-context peak measurements retain their prior evidence. They were not all re-run or simulated as fresh results during this review.

## Open issues and practical limits

1. Cluster authentication health: operator reports `OAuthServerConfigObservationDegraded`, with a timeout connecting to the configured Keycloak provider at 192.0.2.21:443. This is a blocker to declaring full cluster-health and fresh-login acceptance. The cluster administrator must restore/verify connectivity to the configured identity provider and then verify Degraded=False and a new normal login. Do not bypass TLS verification or change the identity provider to hide the failure. A workstation HTTPS discovery request to the configured issuer also timed out during connection; the root cause is not established. Existing inference and authenticated CLI sessions still work.
2. Model-answer quality: unresolved. The reviewed eviction response is application content, not proof the model generates correct commands reliably. Preserve this distinction in demonstrations.
3. RTX 4070 remains outside the reviewed vendor hardware support lists. Functional success does not establish customer support coverage.
4. Argo CD bootstrap/sync and destructive cleanup/restore were not performed. The Application example still requires actual repository, commit, controller namespace, AppProject, and destination values.
5. Fresh installation replay is not proven by dry-run/render tests on an existing cluster. A separate clean project/cluster and maintenance plan are needed for that exercise. No current model data was deleted to manufacture a clean-install claim.

## Source checks

The current [Red Hat AI 3.x matrix](https://access.redhat.com/articles/rhoai-supported-configs-3.x) lists OpenShift 4.22 for AI 3.5. The [NVIDIA 26.7 matrix](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/26.7/platform-support.html) lists RHCOS/OpenShift 4.18–4.22 and driver 595.91.07; its supported GPU list does not include RTX 4070. [MIG-supported hardware](https://docs.nvidia.com/datacenter/tesla/mig-user-guide/supported-gpus.html) remains separate from time-slicing. GitOps guidance was checked against upstream [Kustomize](https://argo-cd.readthedocs.io/en/stable/user-guide/kustomize/), [projects](https://argo-cd.readthedocs.io/en/stable/user-guide/projects/), and [sync options](https://argo-cd.readthedocs.io/en/stable/user-guide/sync-options/) documentation; no installed Argo version is asserted.

## Evidence and next checkpoint

Local inventory files: walkthrough-before.yaml, walkthrough-after.yaml, walkthrough-structure.txt, walkthrough-role-check.txt, walkthrough-chat-check.txt, walkthrough-route-check.txt. Run `python3 checks/review-walkthrough.py` after future documentation/configuration changes. Preserve the initial-install and workload evidence separately.

Next operational checkpoint is authentication health and a fresh login. General model quality remains a separate acceptance task. Use [README](../README.md) as the entry point and [acceptance](acceptance.md) as the current checklist.
