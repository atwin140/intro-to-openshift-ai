# Lab progress — Intro to OpenShift AI

Updated: 2026-09-22. Local lab record; excluded from Git by default.

## Current checkpoint

OAI-00 through OAI-03 are complete. OAI-04 is technically operational but not fully accepted. The model endpoint is Ready on gpu-node-01, one whole GPU, one replica; memory and two-request tests pass. Current provisional model: Qwen2.5-Coder-7B-Instruct-AWQ. Answer quality remains a blocker: supplied facts produce the correct eviction filter but not the complete required explanation, and related questions reveal command errors. Stop before OAI-05 until the quality gate is resolved. See checks/model-quality-review.md. Cloud Work remains paused.

The user authorized local hands-on implementation in stages using the existing authenticated connection. The Work cloud handoff remains paused. No credentials were printed or transferred.

## Initial hardware evidence — before OAI-01, 2026-09-22

- Both `gpu-node-01` and `gpu-node-02` expose one NVIDIA AD104 GeForce RTX 4070, PCI ID `10de:2786`, at guest-local `0000:06:10.0`. Associated audio function `10de:22bc` is not a second GPU.
- Both report `qemu`. The earlier physical-worker description is not supported by the guest evidence. Passthrough is plausible but hypervisor configuration and physical host mapping have not been inspected.
- Neither display controller has an active driver link. No NVIDIA or nouveau module is loaded. `lspci` lists nouveau as a possible module only.
- NVIDIA driver version file and host `nvidia-smi` are absent. Actual VRAM remains pending; 12 GB is still the planning input.
- No guest EFI interface is exposed. The initial node-01 `mokutil` invocation failed for unsupported EFI variables; the corrected collector checks EFI first. The rerun and node-02 run exited successfully. Physical hypervisor firmware was not inspected.
- No diagnostic pods or debug-named namespaces remained. Both workers stayed Ready; all cluster operators remained Available=True/Progressing=False/Degraded=False and both pools Updated=True/Updating=False/Degraded=False.
- Evidence: `inventory/hardware-gpu-node-01-2026-09-22.txt` (initial EFI query failure), `inventory/hardware-gpu-node-01-2026-09-22-recheck.txt`, `inventory/hardware-gpu-node-02-2026-09-22.txt`.

## Initial discovery snapshot — superseded where noted by OAI-01 below

- Authenticated oc user: `darleya`. Context: `default/api-eqip-sharkbait-tech:6443/darleya`.
- Broad administrative authorization check returned `yes`. The later project-user authorization tests are separate and pending.
- OpenShift server 4.22.13; Kubernetes v1.35.6. Cluster update completed. Listed cluster operators and both machine configuration pools report healthy status.
- Five Ready amd64 nodes: `eqip-cp-01`, `eqip-cp-02`, `eqip-cp-03`, `gpu-node-01`, `gpu-node-02`. All report RHCOS 9.8.20260901-0 and kernel 5.14.0-687.44.1.el9_8.x86_64.
- OpenShift AI operator 3.5.1, CSV Succeeded, deployment ready 3/3. No DataScienceCluster exists. `default-dsci` is Ready but reports release 3.5.0; the significance of that version difference is unresolved.
- No NVIDIA GPU resources advertised; NVIDIA and NFD APIs absent. No KServe resources served.
- Default StorageClass: `synology-iscsi-storage`. Provisioning and GPU-worker mounting remain untested.
- Catalog candidates: GPU Operator 26.7.0 in `v26.7`; NFD `nfd.4.22.0-202609081346` in `stable`. These are available bundles, not selected or installed versions.

Detailed node, storage, version, issue, and correction records: [environment review](environment-review.md). Original evidence: `inventory/discovery-2026-09-22.txt`.

## Still reported, not independently established

- Three virtual control-plane machines remain reported. The two GPU workers report QEMU virtualization; physical host mapping is unknown.
- Each RTX 4070 now reports 12282 MiB and passes CUDA computation. Model inference memory and runtime compatibility remain pending.
- Internet-connected cluster; operator catalogs respond, but all required image/model download paths have not been tested.
- Future customer has two H100 GPUs; variants and placement unknown.

## Decisions and assessment

- One model deployment, one replica, one whole GPU. Prepare and test both GPU workers.
- Total device budget is 12 GB, with runtime and conversation-cache headroom; no artificial 8 GB cap.
- No initial MIG or time-slicing.
- Built-in project-scoped `admin` for handoff; Kustomize from the first deployment.
- RTX 4070 is a feasible lab candidate based on CUDA/driver/runtime prerequisites. It is outside the reviewed GPU Operator and Red Hat AI Inference hardware lists. Driver and CUDA operation now pass on both workers; model inference remains untested. See [GPU assessment](../docs/00-gpu-compatibility.md).

## Open items and next checkpoint

1. OAI-00 through OAI-03 complete. OAI-04 runtime is deployed. Resolve its open answer-quality gate before moving to OAI-05.
2. Operator and driver choices are recorded below and in platform Kustomize overlays. Hypervisor configuration remains uninspected, but both guest-visible devices passed computation.
3. Version discrepancy resolved by observed reconciliation: DSCI and DSC now both report 3.5.1, matching the operator CSV. No status fields were manually changed.
4. Later stages: verify image/model access, project-user workload admission, inference memory, command-answer quality, and one-to-two-user behavior.

## Work handoff authorization — paused

The user explicitly approved sending the cluster endpoint, username, node names, storage configuration, and observed infrastructure status to the Work task in Ahead-Eqip. Passwords, tokens, private keys, and kubeconfig credentials are excluded.

Sanitized task creation returned a pending client identifier; no usable destination task ID was located. Detailed discovery results have not been sent. The user subsequently paused this work. Do not restart task creation or ask for approval again without a renewed request to resume the handoff.

## OAI-01 implementation — 2026-09-22

- Selected and installed NFD `nfd.4.22.0-202609151747` (catalog changed from the discovery candidate) and GPU Operator `gpu-operator-certified.v26.7.0`. Both CSVs reached Succeeded. Both subscriptions use Manual approval; exact initial plans `install-nr9fb` and `install-7x8ss` were inspected and approved under the user's installation authorization.
- Applied complete Kustomize operator, discovery, configuration, and validation lab overlays. No synced source files changed. NFD identified NVIDIA hardware only on the two GPU workers.
- Driver image `nvcr.io/nvidia/driver@sha256:e243d778bd83de47668e7629d78f673317a130fedc99941be12aad7fc6bdfa85` reports 595.91.07 in inspected image metadata and in both running drivers. OpenShift Driver Toolkit built the open modules for the current kernel.
- Each GPU reports 12282 MiB total and 1 MiB used at the initial idle measurement. Distinct UUIDs confirm different devices: node-01 `GPU-b30af0f0-628e-64d3-d1ce-6f19803e7146`; node-02 `GPU-f482f14b-15cf-5f03-42eb-4f6aca06f126`.
- Each worker advertises one allocatable GPU; labels report replicas=1 and sharing-strategy=none. MIG strategy is none and MIG Manager is disabled. An operator-created MPS daemonset has desired=0; no MPS sharing is configured.
- CUDA vector addition passed on both workers through separately scheduled jobs using pinned image digest `sha256:86c8ab90b657bc74098f068e670d2635799f1fd3695a0dd55fd696d8f9e3d64b`. Both jobs used restricted pod settings and an account without token mounting or extra permissions. Evidence: `inventory/stage1-evidence-2026-09-22.txt`.
- The temporary `intro-ai-gpu-checks` namespace, test account, jobs, and pods were deleted after evidence capture; namespace absence verified.
- Initial runtime-handler errors resolved after the toolkit configured CRI-O. Monitoring exporters initially failed to connect while the DCGM hostengine image was pulling; both recovered automatically and became Ready after four startup restarts each. Advanced DCP profiling metrics are unsupported on these GPUs and are skipped; no claim is made that all possible metrics are available. No monitoring feature was disabled.
- Model inference, loaded-model memory/headroom, storage, project handoff, and browser behavior remain untested.

Final evidence: `inventory/stage1-final-health-2026-09-22.txt`, refreshed node/policy JSON, and both exporter logs. ClusterPolicy state=ready and Ready=True; all required GPU daemonsets ready=2/desired=2. No MIG manager deployed; MPS control daemonset desired=0. Server dry-run and Kustomize validation are recorded with the stage files.

## OAI-02 implementation — 2026-09-22

- Created `default-dsc` using `datasciencecluster.opendatahub.io/v2` through complete `platform/ai/overlays/lab` Kustomize files. Enabled only dashboard and KServe; all other top-level components Removed. NIM integration, model cache, and workload-variant autoscaler Removed.
- The installed schema supports only RawDeployment. The resulting `inferenceservice-config` confirms defaultDeploymentMode=RawDeployment, disableIngressCreation=true, and enableGatewayApi=false. Model exposure must be planned explicitly during deployment; generic example ingress fields are not proof of installed Knative dependencies.
- Applied `platform/ai-dashboard/overlays/lab` to set disableKServe=false and disableKServeRaw=false. Other existing dashboard settings remained present. Runtime templateDisablement is empty.
- Standard KServe dependencies report AllDependenciesMet. Optional LLMInferenceService/llm-d dependencies (Connectivity Link and LeaderWorkerSet) are absent and reported as informational; they were not installed. KServe's module reports Ready despite those optional capability conditions.
- Existing GatewayConfig `default-gateway` and gateway `openshift-ingress/data-science-gateway` remain Ready/Programmed. Existing cert-manager and Auth settings were retained. Dashboard URL: `https://rh-ai.apps.eqip.sharkbait.tech/`. Unauthenticated HTTPS returned 302 with TLS verification successful; interactive login and actual project-role access remain untested.
- Dashboard and KServe module status report platform=3.5.1. KServe reports upstream release v0.19.0 and runtime family vLLM v0.24.0. Both DSC and DSCI now report 3.5.1; the earlier DSCI 3.5.0 metadata updated during normal reconciliation. No manual status rewrite occurred.
- NVIDIA runtime template: `vllm-cuda-runtime-template`; image `registry.redhat.io/rhaii/vllm-cuda-rhel9@sha256:c056e61672b6aea489ad5dde0bd2f8497230f5333e87f7cf6c494eba3bfdc808`. Operator metadata lists vLLM 0.24.0+rhaiv.13. This is an installed template, not a successful inference test or final model/image selection.
- Initial KServe deployment failed to apply a template while its admission webhook had no endpoints. The controller became Ready and normal reconciliation succeeded; no webhook was bypassed.
- All 11 AI application deployments reached requested replica availability, with InferenceService and ServingRuntime CRDs installed. Dashboard operator also deploys frontend modules; these do not mean the disabled optional backend components were enabled.
- Final cluster operators remain healthy, both machine configuration pools Updated without degradation, and GPU ClusterPolicy Ready. Evidence: `inventory/stage2-evidence-2026-09-22.txt`, `stage2-*-after.json`, deployment/EndpointSlice snapshots, effective configuration, and runtime templates.
- Checkpoint complete; storage, project-admin handoff, model inference, measured loaded-model headroom, and browser chatbot acceptance remain pending. Work cloud handoff remains paused.

## OAI-03 implementation — 2026-09-22

- Created `intro-openshift-ai` with complete `platform/project/overlays/lab` manifests. No quota, new taint, broad role grant, or unrelated resource change.
- Confirmed Synology CSI node registration and healthy CSI pods on both GPU workers. Temporary 1 GiB RWO filesystem claim `storage-handoff-check` bound to `pvc-01ab0450-d1d9-4795-927a-b4ed88ef40f0`.
- Initial write failed with Permission denied. The admitted pod used `openshift-ai-inferenceservice-image-volume-scc` and had no fsGroup. Added the project's allocated group `1000880000` to the lab test security patches; retained non-root, no privilege escalation, dropped capabilities, and no service-account token mount. Do not infer that the initial administrator-created pod exercised the final project user's SCC selection.
- Corrected write on gpu-node-01 returned WRITE-PASSED. Deleted that pod before starting gpu-node-02; the second pod read the same marker and appended data, returning READ-AND-WRITE-PASSED. This validates basic RWO relocation, not concurrent multi-node mounting or performance.
- Saved logs and pod/PVC/PV snapshots in `inventory/stage3-storage-*`. Deleted the temporary pods and PVC; waited for the recorded PV to disappear under its Delete reclaim policy. Project now has no test pods or claims.
- Built-in admin includes KServe InferenceService/ServingRuntime CRUD permissions. Added a RoleBinding base with no subjects (not applied), a permission-check script, and a harmless ConfigMap apply/read/delete test for the actual user. These are prepared, not passed.
- Asked the user which username should receive project admin. Current authenticated identity darleya is cluster-admin and cannot prove restricted handoff. No other user has been selected or granted access. Cloud handoff remains paused.
- Remaining: confirmed username, rolebinding lab overlay, actual separate authenticated session, effective permission checks, Kustomize write/read/delete test, and dashboard project visibility/access. Project-only model deployment must not proceed under an unverified handoff.

### OAI-03 identity follow-up

User selected `ai-user`. Existing OpenShift User confirmed. Applied `platform/project-access/overlays/lab`, creating RoleBinding `demo-project-admin` only in `intro-openshift-ai`. Recorded group membership: `openshift-access`. No matching cluster-admin binding was found in the inspected direct/recorded-group bindings. An administrator preflight with explicit recorded groups allowed creating InferenceServices, ServingRuntimes, Deployments, Routes, and PVCs in the project; patch nodes and create ClusterRoleBindings returned no. This is impersonation evidence only, not final acceptance.

No ai-user context is present among the locally listed contexts. Await the user's normal local authentication as ai-user, then run `checks/project-permissions.py ai-user` and the ConfigMap Kustomize exercise using that login. Do not request or transfer credentials. Evidence: `inventory/stage3-ai-user-rolebinding.json` and `inventory/stage3-ai-user-preflight.txt`. Dashboard access remains pending.

### OAI-03 actual-user checkpoint — complete

- Actual CLI identity is `ai-user` (despite the message saying ai-admin), connected to the recorded EQIP endpoint. No impersonation was used.
- `checks/project-permissions.py ai-user` passed all checked project permissions and denied the checked cluster powers. This does not assert the user lacks every possible cluster-scoped permission.
- Applied, read, and deleted `checks/project-access`; the ConfigMap was absent afterward. No Secret contents were read.
- Found and corrected the missing `opendatahub.io/dashboard: true` namespace label in `platform/project/base/namespace.yaml`. Server dry-run and apply succeeded under the explicitly selected, verified darleya administrator context. The active context remained ai-user.
- Browser first showed darleya. After navigation it showed ai-user; the project list included Intro to OpenShift AI and its overview loaded with Deploy model available. No browser credentials were collected.
- Evidence: `inventory/stage3-actual-user-permissions.txt`, `inventory/stage3-actual-user-handoff.txt`. Prior pending statements in the dated history are superseded. No model or chatbot deployed; cloud handoff remains paused.

## OAI-04 implementation — in progress, 2026-09-22

Selected public Apache-2.0 Qwen/Qwen3-4B-Instruct-2507, pinned revision cdbee75f17c01a7cc42f958dc650907174af0554, BF16 without quantization. Runtime image is pinned to the installed template digest. Complete storage/download/serving Kustomize overlays passed server dry-run as ai-user. 20 GiB Synology claim Bound; downloader admitted under restricted-v2, token mounting false, on gpu-node-01. Image pull/download and all inference measurements remain pending. Local Python HTTPS lacked its CA configuration; native curl retrieved public model metadata with certificate verification intact. No TLS bypass.

Stage 4 progress: model download verified 8,045,591,552 weight bytes, then downloader removed. First download failed because the image defaults HF_HUB_OFFLINE=true; explicit online Job settings fixed it. Runtime reported vLLM 0.24.0+rhaiv.13 / Torch 2.11.0a0+git069d5d8 / CUDA 13.0. KServe generated a Standard deployment from the accepted RawDeployment annotation. It injected kube-rbac-proxy and forced pod token automount true even with the manifest requesting false. Upstream controller source explains this behavior. The final source explicitly disables endpoint platform auth and masks the model container API-token path with a read-only emptyDir. An in-container existence check returned MODEL-API-TOKEN-ABSENT; proxy still has a projected token. Pod uses restricted-v2 on gpu-node-01. No token content was read. Model loading and inference tests remain pending.

Qwen3 4B inference reached Ready, no restarts, and passed network isolation tests. Initial short requests used 10,591 MiB peak with 1,285 MiB free. However, eviction answers failed: nonexistent Evicted conditions and invalid field selectors. Adding a reviewed factual reference still produced malformed jq and misleading explanations; failed outputs and memory evidence retained. Rejecting Qwen3 for this demo. Selected replacement Qwen/Qwen2.5-Coder-7B-Instruct-AWQ revision 8e8ed243bbe6f9a5aff549a0924562fc719b2b8a, public Apache-2.0. Installed AWQ registry accepts its exact config and reports compute minimum 7.5 with FP16/BF16 support. Download in progress; replacement not yet applied to serving. No final quality claim.

### OAI-04 final checkpoint — partial, quality blocker

- Selected coding model revision 8e8ed243bbe6f9a5aff549a0924562fc719b2b8a verified download weight size 5,570,747,392 bytes (5.19 GiB). Red Hat vLLM digest unchanged. FP16 activations, AWQ via MarlinLinearKernel, FlashAttention 2, eager execution.
- One replica/whole GPU on gpu-node-01; Ready, both containers ready, zero restarts. Context 4096, output cap 768, active sequences 2, utilization 0.90.
- Idle 10489 MiB used/1387 MiB free; sampled long-request peak 10865 MiB used/1011 MiB free. Two requests with 3108 input tokens completed in 3.50/3.05 seconds. Oversized input received HTTP 400. Sampling approximately once/second does not capture every transient peak.
- Model container API-token path is an empty read-only volume and existence check passed. Controller-managed proxy retains its projected token. No extra application RBAC granted. Download/validation pods use token automount false.
- Network test: allowed labeled pod HTTP 200; unlabeled pod timed out after DNS succeeded. No public Route. Internal client URL uses :8080 because the Service is headless.
- Qwen3 failed quality and was replaced. Coding model baseline also failed completeness; general prompt rules produced false Evicted-phase and oc -A claims. Explicit static facts improved the filter, but required explanations and oc alternatives remain incomplete. Related history and destructive-command answers also failed review. No generated command was run.
- Do not mark OAI-04 complete. Proposed next correction: reviewed command-reference handling with provenance, then repeat acceptance. No retrieval or browser UI implemented. See the quality review and all retained response JSON.

Final cleanup/consistency: download and network-validation Jobs/ConfigMaps removed; no public Route exists; localhost port-forward stopped. Model and retained PVC remain running/Bound. Final source uses controller-canonical Standard deployment mode; server dry-run/apply passed without a pod replacement. Final network retest passed on the coding-model pod. Four Kustomize overlays render and scripts parse. OAI-04 remains partial solely because the answer-quality gate is unresolved; no Stage 5 work started.

### OAI-04A HTTPS Route checkpoint — 2026-09-22

User requested external model access. Verified ai-user and intended EQIP API before applying complete lab Kustomize patches. OpenShift AI now owns reencrypt Route command-helper at https://command-helper-intro-openshift-ai.apps.eqip.sharkbait.tech, with HTTP redirect and HTTPS proxy target 8443. Route Admitted; InferenceService Ready; one replica, 2/2 containers, zero restarts after an authentication-triggered reload. Initial 55-second rollout wait expired during model loading; subsequent rollout succeeded.

Initial external check failed with 503. Router uses HostNetwork with OVN-Kubernetes; namespace-name selector, even with empty peer podSelector, did not admit traffic. Replaced it with documented policy-group.network.openshift.io/ingress namespace selector, limited to TCP 8443. No system namespace labels or policies modified. Retained existing labeled same-project clients on TCP 8080.

Verified anonymous model listing HTTP 401, authenticated listing HTTP 200, and authenticated chat completion HTTP 200 using ai-user's existing login. TLS validation enabled throughout. No credentials printed or written. Helper captures the token in memory and sends it through curl stdin. Evidence: inventory/stage4-route-test-final.txt and inventory/stage4-route.json. Read-only administrator check confirmed platform-managed intro-openshift-ai-model-server-auth-delegator binding to system:auth-delegator. Model container still returned MODEL-API-TOKEN-ABSENT. Active context remains ai-user.

Endpoint transport passes. Eviction response uses correct reason filtering and namespace examples, but still omits Failed-phase distinction and oc examples; original quality blocker remains. No browser chatbot deployed. Route supplement supersedes earlier internal-only statements. Stop at this checkpoint; cloud handoff remains paused.

Route follow-up: internal NetworkPolicy regression passed: ALLOWED-CLIENT-HEALTH-PASSED and DENIED-CLIENT-TIMED-OUT-AS-EXPECTED. Saved stage4-route-network-* evidence and removed temporary Jobs/ConfigMap. Final model pod 2/2 Ready, zero restarts.

## OAI-05 browser chat — 2026-09-22 implementation, verified 2026-09-23 UTC

User explicitly requested a simple web chat box, authorizing the UI stage despite unresolved general model quality. Applied complete Kustomize resources as ai-user after verifying EQIP API. No cluster-admin writes. URL: https://chat-intro-openshift-ai.apps.eqip.sharkbait.tech. Anonymous edge-TLS Route with HTTP redirect, one chatbot replica, pinned Red Hat Python 3.12 image resolved from installed ImageStreamTag; source ConfigMap rather than a registry build. Containerfile supplied as optional packaging.

Browser verified welcome page, reviewed eviction answer, New chat clearing history, and live model-generated Pod/Deployment response. Limited safe formatting uses text nodes and code-copy buttons. General model quality remains imperfect (including misleading isolation language in later namespace answer); no generated command was executed. The canonical eviction question uses a labeled static reviewed reference and therefore does not establish a model-only quality pass or implement retrieval.

checks/chatbot.py passed reference completeness, client system-role rejection, foreign origin rejection, conversation length rejection, and two simultaneous distinct-marker model requests (0.41/0.44 seconds; no cross-marker in responses). Longer simultaneous requests after final rollout returned HTTP 200 in 5.10/5.57 seconds. Sampled peak 10617 MiB used / 1259 MiB free, sampled about 0.5 seconds plus command overhead. Initial longer-request attempt failed during a concurrent UI rollout; status was not captured on that attempt, so no exact cause is asserted. Final Ready rollout and repeat passed. Evidence: inventory/stage5-chatbot-checks.txt and inventory/stage5-concurrency-memory.json.

Runtime: restricted-v2, read-only filesystem, no added RoleBinding, automountServiceAccountToken=false. In-container token absence and diagnostic TCP connection blocked to Kubernetes API both passed. Egress permits only model TCP8080 and cluster DNS5353; ingress only OpenShift router group8080. UI uses the already-authorized private model path without endpoint credentials; public model API remains authenticated. History stays in browser memory; two previous exchanges are submitted with each question. Server does not persist conversations. Standard HTTP server is a lab-only implementation, with no production hosting claim. One model/whole GPU remains unchanged. Stage 4 broad answer quality, GitOps, second-node inference, and optional exercises remain outstanding; cloud handoff stays paused. Stop at UI checkpoint.

## Context expansion — 2026-09-23 UTC

User requested more context after short stress prompts hit application limits. Verified EQIP API; active user was darleya. All application mutations used the existing explicit ai-user context; did not change the user's active context. Raised model context 4096→16384 and output cap 768→2048; retained one whole GPU, max two active sequences, batched prefill4096, utilization0.90, pinned model/runtime. Runtime reports 4.54GiB KV cache / 85024 token capacity, 5.19x concurrency at16K; actual concurrency remains capped at2. Model reloaded and both Deployments Ready, no restarts.

UI input limit2000→16000 characters, history2→up to20 exchanges. Server payload400000 bytes /96000 conversation characters. Calls installed /tokenize with chat template and system instructions, reserves2048 answer tokens, removes oldest pairs until input<=14336, reports trimming; single oversized question rejects. Browser shows actual input/output tokens, latency, and output-limit completion. Generation timeout120s, browser135s, Route150s. Updated concise-by-default prompt to permit explicitly requested longer answers. No tool execution, credentials, Kubernetes client, or additional permissions added.

checks/chat-context.py passed: two simultaneous requests each12583 input tokens; outputs2048 and787 tokens; HTTP200 in33.4 and17.7seconds. First response correctly reports finish_reason=length. Sampled peak11045MiB used /831MiB free. This is a bounded sample, not a guarantee for every workload or transient peak. Automatic old-history trimming passed. Evidence inventory/context-expansion.json. Basic input/origin/reference/concurrency regression also passed (inventory/context-chatbot-regression.txt). Model-answer quality remains unresolved and no new sustained-load claim is made. Historical 4K limits in earlier progress notes are superseded by this entry. Browser refresh is required for new JavaScript; refreshing clears browser-only history.

## Persistent tone guide — 2026-09-23 UTC

Added the user's five tone rules verbatim to chatbot/prompts/assistant.md. Scoped command formatting to Kubernetes command questions so writing requests do not receive irrelevant command sections. Added factual-grounding instructions for status updates and material-error acknowledgments. Verified intended cluster and applied as explicit ai-user; chatbot rollout succeeded, model configuration unchanged. A fresh request containing no tone guidance returned: “We appreciate your patience. GPU validation is complete, while model-answer validation is still ongoing.” Evidence inventory/tone-guide-check.json. This demonstrates one passing tone example, not guaranteed compliance. System instructions are included on every UI model request, retained during context trimming, and loaded after ConfigMap-triggered rollout. Direct model API callers must supply their own system instructions; static reviewed reference wording is unchanged. Updated Stage5 documentation; Work handoff remains paused.


## Walkthrough review — 2026-09-23

Reviewed the current guide and running EQIP lab. Corrected stage boundaries: deploy/overlays/lab-model now deploys only Stage 4; deploy/overlays/lab composes that overlay with the Stage 5 UI. Combined rendered resources compare byte-for-byte equal before/after. Both overlays passed server dry-run under the existing actual ai-user context; no application resources were changed during this review.

Updated README and acceptance to distinguish current results from dated history, current 16K context / 2048 output limits and 831 MiB sampled headroom, and reviewed static eviction content from model-generated answer quality. Added Stage 6 GitOps guidance, an explicit-placeholder Application template, optional retrieval/H100 modules, and a repeatable structural check. All 37 Kustomize roots rendered; checked Python/shell syntax and local guide links passed. GitOps synchronization and a fresh installation replay remain untested. This directory is not currently a Git repository; no commit was created.

Actual ai-user permission checks passed, including exec/port-forward permissions and denial of checked cluster powers. Live chat regression passed input/reference checks and two simultaneous model calls. Public model endpoint returned anonymous 401 and authenticated listing/completion 200 using darleya. Model and chatbot API-token absence checks passed. Existing tokens working does not prove fresh login. Prior GPU/storage/browser/long-context evidence was retained rather than represented as new tests. Both GPU workers now host workloads: command-helper and the separately validated image-generator; both InferenceServices were Ready. No occupied-GPU test Jobs were launched.

Open issue: authentication ClusterOperator is Available but Degraded with OAuthServerConfigObservationDegraded, reporting a timeout to the configured Keycloak service at 10.0.1.21:443. A workstation HTTPS discovery request to the configured issuer also timed out during connection; this corroborates reachability failure but does not establish its root cause. Cluster administrator owns restoring identity-provider reachability, then verifying Degraded=False and a fresh normal login. No unrelated identity-provider configuration was changed. All five nodes were Ready, machine configuration pools Updated/not Degraded, and NVIDIA/NFD/AI operators and requested platform deployments ready at inspection.

General model-answer quality remains unresolved. RTX 4070 functional lab evidence does not establish vendor hardware support. See checks/walkthrough-review.md and checks/acceptance.md for the current checkpoint. Evidence: inventory/walkthrough-{before,after}.yaml and walkthrough-{structure,role-check,chat-check,route-check}.txt. Cloud Work handoff remains paused; synced sources were not modified.


## Reset and two-cluster reuse — 2026-09-23

User clarified that the planned labs are two separate clusters, each with one RTX 4070. Added scripts/reset-lab.py and docs/08-reset-and-reuse.md with separately gated project, AI-component and GPU-operator teardown stages. Project reset is recommended for routine participant turnover; dedicated-cluster/GPU-worker reprovisioning is recommended when the course requires a clean driver/operator baseline. Existing two-worker profiles are not yet adapted or validated for the new clusters.

Preview verified the intended EQIP API and cluster ID, enumerated command-helper and image-generator and both Delete-policy model PVs. No deletion or configuration mutation occurred. Default is preview; execution requires expected cluster ID, exact stage confirmation, dedicated-scope acknowledgement and cluster-admin. Script checks GitOps ownership, shared workloads, expected binding/operator scope and deletion checkpoints; never force-clears finalizers or reads Secret contents. AI operator/DSCI/gateway/identity prerequisites predate the lab and are retained; CRDs and possible host/operator residue are explicitly not claimed removed. Added security-group reallocation warning for recreated namespaces. Mock tests cover guards, ordering and fail-stop behavior; live destructive teardown and redeployment remain untested. Work handoff remains paused.


## Reset preview correction

User supplied GPU command with --confirm and --ack-dedicated-lab but no --execute. It correctly made no changes, but preview text misleadingly said Delete and described removal checkpoints. Corrected preview messages and reject confirmation flags without explicit execution before any cluster calls. Regression tests cover this exact command pattern and preview wording. Read-only inspection found demo project and DSC absent, GPU/NFD operators still installed, and authentication Degraded=False. No reset was executed during this correction; platform teardown remains unvalidated.


## Public Git preparation — 2026-09-23

Initialized a local main-branch Git repository in intro-to-openshift-ai and staged the shareable source. No remote URL supplied; no push performed. Public source now uses example domains, worker names, administrator identity and filesystem group. Original candidate files preserved in ignored inventory/pre-public-review.tar.gz; private notes/inventory and synced sources are excluded. Fixed missing output-directory creation in evidence checks, removed links into private excluded files, expanded public Markdown link checks, and added workstation/generated ignores.

Added new-cluster setup and a one-GPU CUDA validation overlay. Explicit local edits remain required for each cluster. Added six local chatbot HTTP tests (stub inference, no GPU) and a credential-pattern scan; 18 reset safety tests pass. All 38 Kustomize roots render. Isolated 139-file Git-index export passed all four checks without private notes/inventory; single-GPU overlay renders exactly one Job. No fresh GPU/inference or full reinstall was attempted. Read-only observation: demo/GPU/NFD namespaces absent after reset; authentication Degraded=False. Release report separates historical acceptance from current readiness. Public repo license remains undecided pending owner input; Work cloud handoff remains paused.
