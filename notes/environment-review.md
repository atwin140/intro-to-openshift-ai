# Lab environment review — 2026-09-22

Initial OAI-00 snapshot below; the OAI-01 update at the end supersedes GPU readiness and installed-operator facts.

Local evidence and findings for OAI-00. This file is excluded from Git. Reusable instructions remain under `docs/`. The review includes read-only API requests, two unsuccessful strict SSH connection attempts, and later authorized temporary node-debug diagnostics. No persistent cluster configuration was changed.

## Observed environment

| Area | Observed value | Interpretation |
| --- | --- | --- |
| Identity/context | `darleya`; `default/api-eqip-sharkbait-tech:6443/darleya` | Local authenticated API access works; no credential material recorded |
| Authorization | `oc auth can-i '*' '*' --all-namespaces` returned `yes` | Broad administrative authorization observed; this is not the later project-user permission test |
| Server | OpenShift 4.22.13; Kubernetes v1.35.6; CRI-O 1.35.6 | Reported server version confirmed |
| Client | `oc` 4.21.0; embedded Kustomize v5.7.1 | Current discovery commands work; use a matching 4.22 client for subsequent version-specific procedures |
| Release | 4.22.13 Completed at 2026-09-17T23:04:59Z; Available=True, Failing=False, Progressing=False | No update in progress at collection time |
| Cluster operators | All listed Available=True, Progressing=False, Degraded=False | No cluster-operator health blocker observed |
| Machine configuration pools | Master 3/3, worker 2/2; Updated=True, Updating=False, Degraded=False | No unfinished machine configuration rollout observed |
| OS/kernel | All nodes: RHCOS 9.8.20260901-0; 5.14.0-687.44.1.el9_8.x86_64; amd64 | Driver compatibility must match this actual host stack |

### Nodes

Memory figures below are converted from the API's Ki values and rounded. Capacity is not unused capacity. Allocatable is the amount Kubernetes can assign before subtracting existing pod requests.

| Nodes | State / roles | CPU capacity / allocatable | RAM capacity / allocatable | Taints / GPU resources |
| --- | --- | --- | --- | --- |
| `eqip-cp-01`, `eqip-cp-02`, `eqip-cp-03` | Ready; control-plane, master, worker | 32 / 31.5 cores each | 62.8 / 61.7 GiB each | None / no `nvidia.com/gpu` |
| `gpu-node-01`, `gpu-node-02` | Ready; worker | 8 / 7.5 cores each | 47.0 / 43.9 GiB each | None / no `nvidia.com/gpu` |

Observed internal addresses for hardware follow-up: `gpu-node-01` = `10.0.15.229`; `gpu-node-02` = `10.0.15.150`. Direct SSH with strict host-key checking failed because no trusted ED25519 host key was available for either address. Those SSH attempts collected no host evidence. Subsequent API-based node diagnostics collected the hardware evidence below without changing SSH trust. This is a blocker for that SSH inspection path, not evidence of GPU failure or a reason to bypass host verification.

### Hardware follow-up through the authenticated API

| Worker | NVIDIA display controllers | Identity / guest PCI address | Virtualization | Driver / firmware |
| --- | --- | --- | --- | --- |
| `gpu-node-01` | 1 | RTX 4070 AD104, `10de:2786`, `0000:06:10.0` | qemu | No active GPU driver; no guest EFI interface |
| `gpu-node-02` | 1 | RTX 4070 AD104, `10de:2786`, `0000:06:10.0` | qemu | No active GPU driver; no guest EFI interface |

The matching PCI addresses are local to each guest. These observations establish two guest-visible GPUs across the two workers, not their physical host mapping. The earlier bare-metal/physical-worker assumption is corrected. PCI passthrough is an inference; no hypervisor settings have been inspected. NVIDIA lists VM passthrough as a deployment option, but GeForce remains outside the reviewed product hardware lists.

`lspci` lists nouveau as a possible module; `/proc/modules` and the empty driver symlink show it is not active. Neither NVIDIA driver version data nor host `nvidia-smi` is present. Actual VRAM and CUDA operation are deferred to OAI-01. The first node-01 diagnostic returned nonzero only because `mokutil` could not access EFI variables. The script now checks for the EFI interface first; both final runs succeeded. This does not verify the physical hypervisor's Secure Boot state.

Temporary pods `gpu-node-01-debug-r56qz`, `gpu-node-01-debug-v4c4w`, and `gpu-node-02-debug-z2kqc` were removed. No debug-managed pods or debug-named namespaces remained. Both workers stayed Ready; postcheck operator and pool conditions remained healthy. No SSH trust, driver, taint, label, or host package changes were made.

Evidence is in the three `inventory/hardware-gpu-node-*-2026-09-22*.txt` captures, including the preserved initial failure. Diagnostic image digest is recorded in [OAI-00-H](../docs/00-hardware-discovery.md).

### OpenShift AI and related operators

- OpenShift AI `rhods-operator.3.5.1` in `redhat-ods-operator`: CSV Succeeded. Deployment `rhods-operator`: 3 ready replicas out of 3 requested.
- Subscription: `stable-3.x`, `redhat-operators`, Automatic approval.
- DataScienceCluster: empty list. No serving stack configuration is established by this inventory.
- `default-dsci`: `dscinitialization.opendatahub.io/v2`; Ready, Available=True, Degraded=False. Release field says 3.5.0. Metrics, traces, and alerting report not configured. These observations are not themselves proof of a broken installation.
- Applications namespace: `redhat-ods-applications`; monitoring namespace: `redhat-ods-monitoring`.
- NVIDIA ClusterPolicy and NFD APIs are not served. No `serving.kserve.io` resources appear. OLM v1 ClusterExtension list is empty.
- cert-manager operator 1.20.0 is already installed. Its compatibility with the eventual serving path still needs validation; avoid installing a duplicate.
- Available GPU package default `v26.7` points to `gpu-operator-certified.v26.7.0`; `stable` currently points to the same bundle. `v26.3` points to 26.3.3. Many older channels remain visible. Availability does not establish support.
- NFD package default `stable` points to `nfd.4.22.0-202609081346`.

### Storage

| StorageClass | Default | Provisioner | Binding / reclaim |
| --- | --- | --- | --- |
| `synology-iscsi-storage` | Yes | `csi.san.synology.com` | Immediate / Delete |
| `postgress-synology-storage` | No | `csi.san.synology.com` | Immediate / Delete |
| `ocs-storagecluster-ceph-rbd` | No | `openshift-storage.rbd.csi.ceph.com` | Immediate / Delete |
| `ocs-storagecluster-cephfs` | No | `openshift-storage.cephfs.csi.ceph.com` | Immediate / Delete |
| `openshift-storage.noobaa.io` | No | `openshift-storage.noobaa.io/obc` | Immediate / Delete |

The NooBaa class serves object bucket claims; it is not interchangeable with a filesystem PVC class. New PVC provisioning, data writes, and volume attachment on the GPU workers are not tested. GPU relocation may also require storage detach/attach or different access modes. OAI-03 must test the storage chosen for the model rather than assuming the default is suitable. Review data retention before later cleanup because the listed reclaim policies are Delete.

## Findings and required actions

| Finding | Classification and impact | Owner / next action |
| --- | --- | --- |
| RTX 4070 omitted from reviewed GPU Operator and Red Hat inference hardware tables | Support limitation; functional lab operation remains possible but unproven | Guide author and cluster owner: follow the GPU assessment and validate each worker; do not label it customer-supported |
| No driver/device-plugin readiness; guest GPU inventory now collected | Expected preparation gap; model deployment cannot yet use GPUs | Cluster-admin: complete OAI-01 computation and memory checks |
| No DataScienceCluster | Expected configuration gap; serving deployment is not ready | Cluster-admin: configure only verified prerequisites in OAI-02 |
| DSCI release 3.5.0 differs from CSV 3.5.1 | Unresolved version metadata; no failure inferred | Guide author: check patch release/operand metadata before recording full serving compatibility |
| Control-plane nodes also have worker roles and no taints | Placement risk; generic worker selectors can match them | Cluster-admin/guide author: use actual GPU resource requests and verified placement; do not taint control-plane nodes as an incidental change |
| Worker allocatable capacity is below nominal hardware sizing | Sizing consideration; workloads already consume part of it | Guide author: inspect existing pod requests before setting model CPU/RAM requests |
| Default storage is Synology iSCSI | Untested dependency on GPU-worker networking and CSI node support | Cluster-admin: OAI-03 provisioning/mount test on relevant workers |
| AI subscription uses Automatic approval | Reproducibility risk; future installed versions can change | Cluster owner: review update policy before final version pinning; no policy change made |
| Client is one minor version behind server | Tooling alignment item, not a demonstrated failure | Cluster owner: use matching 4.22 CLI before following version-specific deployment commands |
| SSH host identity not established from this workstation | Blocks this direct hardware inspection path | Direct SSH remains unused; authenticated node-debug diagnostics completed hardware inventory without changing trust |

No observed cluster-operator or node readiness failure currently prevents documentation work. GPU and serving preparation remain required before the model can run.

## Documentation and collector corrections

- Replaced stale “all versions unknown” language with observed server/operator facts and separate unverified component/hardware facts.
- Added a sourced RTX 4070 assessment that distinguishes CUDA capability, Linux driver support, upstream vLLM requirements, product support, and actual lab tests.
- Replaced the old 26.3-only research reference with current candidate review. No operator/driver version is silently selected.
- Kept exact lab identifiers and state in ignored local notes; reusable guide text explains the general checks.
- Filtered copied CSVs using the observed `olm.copiedFrom` label. The old collector printed the same operators across many namespaces.
- Added bounded request timeouts and nonzero exit status for failed reads. A successful collection still does not mean a healthy or compatible cluster.
- Clarified that `.gitignore` does not discover secrets and does not transfer local notes into a clean Git clone.
- Preserved the stage boundary: no deployment-ready manifests, GPU tests, storage tests, or completed acceptance claims have been fabricated.

## Evidence locations and follow-up

- Original unmodified capture: `inventory/discovery-2026-09-22.txt`.
- [Progress and next checkpoint](lab-progress.md).
- [Official compatibility research](../docs/00-gpu-compatibility.md).
- Reviewed collector capture: `inventory/discovery-2026-09-22-reviewed.txt`; completed with zero failed reads. Optional GPU/serving APIs remain absent as recorded above.

## Verification completed

- Shell syntax check passed.
- Collector ran against the lab without failed API reads. Health findings remained consistent with the original capture. Copied CSV filtering reduced the capture from 1,306 to 470 lines.
- Simulated successful collection, partial read failure, and failed authentication returned the expected exit statuses. Partial read failure continued independent collection; absent optional APIs were reported without a false read failure.
- Local Markdown links resolve. The known private-note links remain intentionally excluded from a clean Git clone.
- The package-name filter was tightened so the heading pattern does not also match `namespace-configuration-operator`.
- No GPU computation workload, model endpoint, storage provisioning, or project-user test was run; those acceptance items remain unchecked.

## OAI-00 checkpoint disposition

Discovery is complete with uncertainty recorded, not GPU readiness certified. OAI-01 must validate the driver and CUDA on both workers; OAI-02 must reconcile AI component versions; OAI-03 must validate storage and project permissions. The documented 12 GB budget is still reported, not measured. Cloud Work remains paused.

## OAI-01 update — drivers and CUDA verified

NFD 4.22.0-202609151747 and GPU Operator 26.7.0 are installed with manually approved subscriptions. The updated NFD bundle was observed in the catalog before selection; no version was silently substituted. Driver 595.91.07 open kernel modules load successfully on both QEMU workers. Each reports 12282 MiB and one allocatable GPU, with distinct GPU UUIDs. Both pinned CUDA vector-add Jobs passed on their specified nodes. This supersedes the initial no-driver/no-resource findings.

ClusterPolicy is Ready. All required GPU daemonsets are ready on both nodes. Monitoring startup failures resolved without disabling monitoring; the exporters skip unsupported advanced profiling metrics. MIG strategy=none; MIG Manager disabled; replicas=1 and sharing-strategy=none. The MPS control daemonset created by the operator has desired=0 and no sharing configuration.

The test namespace/account/jobs were removed after saving evidence. All nodes remain Ready, all cluster operators Available without degradation/progression, and both machine configuration pools Updated without degradation/updating. No persistent host configuration was changed outside the authorized operator-managed GPU setup. Model inference and loaded-model headroom remain unvalidated; vendor-support limits remain unchanged.

See [OAI-01](../docs/01-gpu-enablement.md), [platform files](../platform/README.md), and [progress/evidence](lab-progress.md). The DSCI version discrepancy, storage validation, and project-role handoff remain later-stage items.

## OAI-02 update — serving platform ready

The initial missing-DataScienceCluster finding is resolved. `default-dsc` now enables dashboard and KServe through the platform Kustomize overlay. Both modules and the DSC report Ready; all 11 AI application deployments are available. InferenceService and ServingRuntime APIs are installed. Effective deployment mode is RawDeployment; no automatic model ingress is enabled by the KServe config.

DSCI release metadata updated from 3.5.0 to 3.5.1 during reconciliation. It now matches DSC and operator metadata, without manual status changes. The previous discrepancy is closed. KServe reports v0.19.0 and the supplied vLLM template belongs to the 0.24.0 runtime family; actual inference remains untested.

The pre-existing OpenShift AI gateway remains healthy. Dashboard HTTPS reaches a login redirect with valid TLS. The existing Auth allows system:authenticated and identifies rhods-admins as AI administrators; these settings were not changed. Project role and interactive access tests belong to OAI-03.

Optional distributed-serving prerequisites are absent but the KServe module reports all standard dependencies met. The initial admission-webhook startup race recovered automatically. No extra dependency operators were installed and no webhook/TLS verification was bypassed. See [Stage 2](../docs/02-openshift-ai.md) and [progress evidence](lab-progress.md).

## OAI-03 update — storage validated, identity pending

Synology iSCSI provisioned and attached a disposable filesystem volume to both workers sequentially. The first write exposed a missing fsGroup under the administrator-selected AI SCC; the namespace-allocated group resolved it without extra privileges. The second worker verified the first worker's persisted data and wrote successfully. Cleanup verified the test PV's deletion. This closes basic physical-worker storage connectivity/mount uncertainty, but model-size capacity and performance are not benchmarked.

Project `intro-openshift-ai` exists. No handoff identity was assumed from the available user list. The real non-cluster-admin login remains required; stage completion and project-only execution are blocked on that input and verification. No credentials were requested or printed.

## OAI-03 final update — actual-user handoff verified

The actual ai-user CLI session passed the permission script and Kustomize ConfigMap create/read/delete test. The namespace dashboard label omission was corrected in Kustomize and applied through the separate administrator context, without switching the active ai-user context. Dashboard project list and project overview were observed under ai-user. Stage 3 is complete; later model/application admission, inference, and browser-chatbot checks are pending. See the progress record for evidence paths.

## OAI-04 update — inference works, answer quality open

The RTX 4070 now has actual inference evidence: pinned Red Hat vLLM served Qwen3 BF16 and Qwen2.5-Coder AWQ; the latter is currently Ready. Both short and two longer requests ran with measured headroom (minimum free 1011 MiB). This establishes tested lab operation on gpu-node-01, not vendor support or inference testing on gpu-node-02. Both workers previously passed CUDA/storage tests. Stage 4 acceptance remains open because model answer quality failed; see checks/model-quality-review.md.

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
