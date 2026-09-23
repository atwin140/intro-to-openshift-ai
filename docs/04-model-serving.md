# OAI-04 — Serve and test the command-help model

Applicability: reference OpenShift 4.22.13, OpenShift AI 3.5.1, standard KServe serving (the controller normalizes RawDeployment to Standard); one RTX 4070. This is a lab validation, not a vendor-supported GPU certification. Stage 3 must pass first.

## Objective, role, and concepts

Deploy one instruction-tuned model through OpenShift AI, then verify command quality, memory headroom, and two simultaneous requests. Required role: built-in project-scoped `admin` in `intro-openshift-ai`, authenticated as `ai-user`. Administrator-only infrastructure checks remain separate. Application changes run as project administrator. Enabling endpoint authentication asks the installed platform controller to manage its authentication-delegation ClusterRoleBinding; project administrators do not create that binding themselves.

Instruction tuning teaches a model to respond to requests. The serving runtime loads its weights and generates tokens (pieces of text). BF16/FP16 store unquantized weights in approximately two bytes. AWQ stores many weights at four bits, while some layers and quantization metadata use additional space. The key/value cache holds intermediate conversation calculations. Weights, cache, and runtime overhead must fit together; parameter size alone does not establish GPU fit.

## Model comparison and selection

| Candidate | Weight-only estimate | License/access | Runtime and selection considerations |
| --- | --- | --- | --- |
| `Qwen/Qwen3-4B-Instruct-2507` | 4.02B BF16 parameters, about 7.49 GiB | Apache 2.0; public, ungated | Tested and rejected for this demo: inference and memory passed, but eviction answers failed even with a factual reference. |
| `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ` | 7.61B parameters; verified weight files 5.19 GiB, including unquantized layers | Apache 2.0; public, ungated | Replacement selected for testing: coding-focused model with AWQ quantization accepted by the installed runtime. Runtime tests pass, but answer quality remains below acceptance; selection is provisional. |
| `microsoft/Phi-4-mini-instruct` | 3.8B, approximately 7.1 GiB at two bytes/parameter | MIT; public model card | Plausible alternative with published vLLM examples. Not benchmarked here; validate exact image/architecture before substitution. |
| `Qwen/Qwen2.5-3B-Instruct` | 3.09B, approximately 5.8 GiB | Qwen Research license; public model card | Lower memory starting point, but its license differs from the Apache-licensed Qwen variants. Not selected or locally benchmarked. |

The Qwen3 rejection is based on local answer tests; the other untested alternatives are a requirements comparison, not a measured ranking. The model cards' general coding scores do not establish OpenShift expertise. The replacement uses the publisher's AWQ 4-bit weights (activation-aware weight quantization), FP16 activations, and the installed runtime's AWQ implementation. The runtime reports minimum compute capability 7.5, below RTX 4070's 8.9, and accepted this exact config: group size 128, zero point true. Final kernel compatibility requires successful loading/inference. No GPTQ or FP8 compatibility is assumed.

Pinned selection:

- Model revision: `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a`.
- Image from the installed NVIDIA ServingRuntime template: `registry.redhat.io/rhaii/vllm-cuda-rhel9@sha256:c056e61672b6aea489ad5dde0bd2f8497230f5333e87f7cf6c494eba3bfdc808`.
- One replica, one whole GPU; initial placement `gpu-worker-01`.
- Context limit 16384 tokens (input plus output), output cap 2048 tokens, at most two active sequences. More requests can queue; this is not an HTTP admission/rate limit.
- GPU memory utilization 0.90. This runtime allocation budget is not a hardware partition. Eager execution avoids CUDA-graph allocations for the initial small lab; performance is measured rather than assumed.
- 20 GiB Synology RWO PVC. It retains model files after pod replacement. It is not a backup; deleting the claim uses the StorageClass Delete reclaim policy.

## Inspect first

From the repository root, verify identity and endpoint. These values must match the intended lab before applying:

```bash
mkdir -p inventory
oc whoami
oc whoami --show-server
python3 checks/project-permissions.py ai-user
```

Expected identity: `ai-user`; API: `https://api.lab.example.com:6443`.

## Download the pinned weights

The download Job uses the pinned runtime image's existing Python/Hugging Face library. This image defaults to offline operation; the Job explicitly sets `HF_HUB_OFFLINE=0` and `TRANSFORMERS_OFFLINE=0`. The inference container retains offline mode. It does not install packages, request a Hugging Face token, or load remote Python model code. It downloads weights, configuration, tokenizer files, README, and license from the exact revision. Its service account has no role binding or mounted API token. The lab overlay supplies the namespace's allocated filesystem group, `1000000000`; verify and replace it when reusing another project.

```bash
oc apply --dry-run=server -k deploy/storage/overlays/lab
oc apply -k deploy/storage/overlays/lab
oc apply --dry-run=server -k deploy/download/overlays/lab
oc apply -k deploy/download/overlays/lab
oc get pods,pvc -n intro-openshift-ai -o wide
oc logs -f job/download-model -n intro-openshift-ai
oc wait --for=condition=Complete job/download-model -n intro-openshift-ai --timeout=60s
```

Image pull and download can take longer than one minute; inspect progress and repeat the bounded wait. Expected: a Bound 20 GiB claim, Job Complete, and `DOWNLOAD-VERIFIED` with weight bytes. Inspect pod events if no logs exist yet. Record logs before deleting the completed downloader; keep the PVC:

```bash
oc logs job/download-model -n intro-openshift-ai > inventory/stage4-download.txt
oc delete -k deploy/download/overlays/lab
```

## Serve through KServe

The model loads `pvc://model-cache/qwen-coder-7b`. The ServingRuntime is based on the installed OpenShift AI template. The installed controller normalizes the older `RawDeployment` annotation to `Standard`; the final manifest uses the observed canonical `Standard` value to avoid persistent configuration drift. KServe creates the actual Deployment and Service. Do not independently create a second Deployment or use the dashboard deployment wizard for the same model.

```bash
oc apply --dry-run=server -k deploy/overlays/lab-model
oc apply -k deploy/overlays/lab-model
oc get inferenceservice,servingruntime,pods,svc -n intro-openshift-ai
oc wait --for=condition=Ready inferenceservice/command-helper -n intro-openshift-ai --timeout=60s
```

The reusable base is internal. The lab overlay now enables an authenticated HTTPS Route through the installed OpenShift AI controller. See [OAI-04A: HTTPS model access](04a-model-route.md). The ingress NetworkPolicy permits TCP 8080 from same-project pods labeled `intro-ai-model-client=true`, and TCP 8443 from the OpenShift ingress namespace group. Only the proxy port is exposed through the Route. Project administrators can assign the internal client label; this is a lab network boundary, not per-user authentication. Port-forward testing uses authorized Kubernetes access and does not test the Route or pod-to-pod policy.

Placement uses the existing hostname label to make tests reproducible. No node taints or tolerations are added. `Recreate` avoids needing two GPU allocations during a model update. Service-account token automount is requested false. In this installed version, the controller nevertheless injects a kube-rbac-proxy and forces pod-level automount true. The model container mounts an empty read-only volume at the API-credential path so its process receives no API token; the platform proxy retains its token. No additional application RoleBinding is granted. This is a documented platform exception, not a claim that the entire pod is token-free. Examine the admitted pod to verify these settings; resource admission success is separate from role authorization.

## Endpoint and memory checks

With lab endpoint authentication enabled, the generated headless Service exposes HTTPS port 8443. Its direct, network-restricted HTTP pod-address URL remains below; its pod-address URL is `http://command-helper-predictor.intro-openshift-ai.svc.cluster.local:8080`. Headless DNS resolves directly to pod IPs, so internal clients must use 8080. In another terminal:

```bash
oc port-forward --address=127.0.0.1 -n intro-openshift-ai deployment/command-helper-predictor 18080:8080
```

Keep that terminal open. Run `python3 checks/model-memory.py` from the repository root; it invokes `checks/model-endpoint.py` while sampling GPU use. Stop the port-forward with Ctrl-C afterward. The script sends prompts and saves answers; it never executes generated commands. Record GPU usage before and during requests using `nvidia-smi` inside the model pod, where the assigned device is visible. Record the pod image ID, node, security context, restart count, and logs.

Review the evicted-pod answer manually. `Failed` is a phase covering more than eviction. Filter the returned objects by `status.reason == "Evicted"`, for example with `jq`. `-A` means all namespaces; omitting it means the current namespace; `-n NAME` selects one namespace. Both oc and kubectl examples should work. Do not accept an unsupported `status.reason` field selector. Do not execute model-generated commands automatically.

Verify the actual pod-to-pod network boundary separately:

```bash
oc apply -k checks/model-network/overlays/lab
oc wait --for=condition=Complete job/model-network-allowed job/model-network-denied -n intro-openshift-ai --timeout=60s
oc logs job/model-network-allowed -n intro-openshift-ai
oc logs job/model-network-denied -n intro-openshift-ai
oc delete -k checks/model-network/overlays/lab
```

Expected: labeled client receives HTTP 200 and unlabeled client times out after successful DNS resolution. Neither test mounts an API token or requests a GPU. Save both results before cleanup.

## Console inspection alternative

In OpenShift AI, choose **Projects → Intro to OpenShift AI → Deployments**. Inspect the model's status. Use the OpenShift console to inspect its pod, logs, events, and PVC. Kustomize has no equivalent console click-through deployment workflow; importing YAML is an alternative but does not replace the repository as source of truth.

## Common failures

- ImagePullBackOff: inspect events for registry authorization or connectivity. Never print pull-secret contents. Move any required cluster pull configuration to administrator preparation.
- Download failure: inspect the Job logs, PVC permissions, DNS, TLS, and available space. Never disable TLS validation. Delete only the failed download Job/configuration after saving evidence, then reapply the corrected overlay; keep the PVC for resumable downloads.
- OOM or insufficient KV cache: inspect startup memory profiling. Reduce context or cache/concurrency demand; do not silently change the model or claim capacity from weight-only arithmetic.
- OfflineModeIsEnabled during download: retain the Job's explicit online settings. The first lab attempt failed because it inherited offline mode; the failed Job was saved as evidence before correction.
- CUDA/attention error: record runtime CUDA version, driver, architecture, and full failure evidence before selecting a documented compatible backend.
- Forbidden or SCC rejection: correct project-scoped security settings; do not grant privileged or anyuid merely to make inference work.
- PVC multi-attach: ensure the previous pod is stopped before relocating; do not force detach a live volume.
- Incorrect command answer: record failure, improve general instructions or reconsider the model, and rerun independent prompts. A passing single prompt does not prove broad correctness.

## Recorded technical results and open quality gate

The table below records the original 4,096-token test. The current 16,384-token configuration was subsequently tested with two simultaneous 12,583-token inputs: 11,045 MiB peak sampled use, 831 MiB minimum sampled free, and 33.4/17.7-second responses. See `checks/chat-context.py` and the local context-expansion evidence.

The selected coding model reached Ready on gpu-worker-01, one replica/one GPU, with zero restarts. AWQ used MarlinLinearKernel and FlashAttention 2. Model API-token absence passed; the platform proxy token exception remains documented above. Allowed and denied client network tests passed.

| Measurement | Result |
| --- | --- |
| GPU capacity reported by nvidia-smi | 12282 MiB |
| Model idle used/free | 10489 / 1387 MiB |
| Short single/two-request observed peak used | 10489 MiB |
| Two longer requests (3108 input tokens each), observed peak used/free | 10865 / 1011 MiB |
| Longer-request elapsed times | 3.50 and 3.05 seconds |
| Context overflow | Rejected with HTTP 400 |

Memory is sampled about once per second, so these are observed peaks rather than an assurance that every transient allocation was captured. Driver-reserved memory explains why used plus free is less than total. The serving engine preallocates its conversation cache, so idle use is already substantial. These are short lab tests, not sustained-load qualification.

Answer quality is a blocker to the full stage checkpoint. The eviction filter is correct only after supplied facts, and required explanations/oc alternatives remain incomplete. A related answer suggested a malformed destructive pipeline; nothing executed it. The [quality review](../checks/model-quality-review.md) records all failures and the expected correct answer. The user authorized the browser lab with this limitation retained. Stage 5 provides a separately labeled reviewed eviction reference; it does not establish a model-only quality pass.

Repeat the additional context and factual checks with:

```bash
python3 checks/model-memory.py --test boundaries --output inventory/stage4-boundary-memory.json
```

## Completion checkpoint and cleanup

Complete only when the InferenceService is Ready, actual inference passes, one/two-request memory measurements retain headroom without OOM, the acceptance answer is correct, and the admitted workload respects the project-role/security boundary. For a new walkthrough, stop at this checkpoint. Advancing with an unresolved quality gate is an explicit lab decision, recorded separately from a passing model-quality result.

To stop serving while retaining downloaded files:

```bash
oc delete inferenceservice command-helper -n intro-openshift-ai
oc delete servingruntime lab-vllm -n intro-openshift-ai
oc delete networkpolicy model-ingress -n intro-openshift-ai
```

Reapply the lab overlay to restore service. Do not use `oc delete -k deploy/overlays/lab-model` casually: it also deletes the PVC and its model files. Full cleanup requires reviewing that data deletion first. Cluster-admin resources are not part of this overlay.

## Model-selection evidence

The persistent volume currently retains the rejected Qwen3 files in a separate directory for comparison; clean deployments download only the selected coding model.

The initial Qwen3 4B runtime test succeeded with about 1.25 GiB free, but both the unassisted and reference-assisted eviction answers failed. They invented condition types or malformed filters. Evidence is preserved in `inventory/stage4-responses-baseline-failed.json` and `inventory/stage4-responses-qwen3-reference-failed.json`. This is why the deployment source now selects the coding model. A reviewed reference did not repair those failures, so it is not used to conceal the baseline result. The current prompt includes behavior instructions and reviewed static Kubernetes facts. These facts improved the selected model's filter, but the complete acceptance answer still failed. The client supplies the prompt per request; the runtime does not automatically read the Markdown file. See the [quality review](../checks/model-quality-review.md).

## Sources

- [Rejected Qwen3 model card](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507)
- [Qwen2.5 alternative model card](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct)
- [Phi-4-mini alternative model card](https://huggingface.co/microsoft/Phi-4-mini-instruct)
- [vLLM 0.24 supported architectures](https://docs.vllm.ai/en/v0.24.0/models/supported_models/)
- [vLLM 0.24 serving flags](https://docs.vllm.ai/en/v0.24.0/cli/serve/)
- [OpenShift AI 3.5 model deployment and PVC storage](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html/deploying_models/deploying_models)

Runtime inspection reported vLLM `0.24.0+rhaiv.13`, PyTorch `2.11.0a0+git069d5d8`, and CUDA build `13.0`. Installed driver `595.91.07` exceeds the CUDA 13.x minimum driver branch 580. [NVIDIA driver compatibility](https://docs.nvidia.com/deploy/cuda-compatibility/minor-version-compatibility.html). This prerequisite check does not replace actual inference testing.

- [Upstream OpenDataHub KServe proxy injection source](https://github.com/opendatahub-io/kserve/blob/7d068b1b3b316e6e49e8002b36dc270280ffaabe/pkg/controller/v1beta1/inferenceservice/reconcilers/deployment/deployment_reconciler.go) — inspected to explain observed proxy and token behavior; this upstream revision is not asserted to be the exact installed image build.

- [Qwen2.5-Coder-7B-Instruct-AWQ model card](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct-AWQ)
- [vLLM quantization hardware table](https://docs.vllm.ai/en/latest/features/quantization/) — current upstream guidance, cross-checked against installed runtime class/config acceptance.
