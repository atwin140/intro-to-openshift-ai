# OAI-00 — Discover the environment

Version applicability: OpenShift Container Platform 4.22 and OpenShift AI 3.5. Official sources reviewed on 2026-09-22. This reusable procedure does not presume a new environment's state. In this lab, server 4.22.13 and operator 3.5.1 have now been observed; see the separate lab review (private local evidence; excluded from the public repository). If discovery reports other versions, reassess compatibility before installing anything.

## Objective and purpose

Establish what is installed, whether the cluster is healthy, and which facts are still missing. This prevents choosing drivers or serving components for the wrong environment.

The API inventory below reads cluster configuration only. For separately authorized temporary node diagnostics, use [OAI-00-H](00-hardware-discovery.md). This read-only portion does not install operators, create workloads, change labels or taints, or test new storage provisioning. A read-only inventory cannot prove that a new volume will provision or that GPU computation will succeed.

## Required role and prerequisites

- Cluster-admin, as already reported.
- Access to the intended lab's web console.
- A terminal with `oc` and Bash, authenticated to that same cluster. Do not install the Web Terminal Operator just to run discovery; use your existing administration workstation.
- The repository directory on that workstation if using the collector. The script needs no `jq` or Python.

## Compatibility findings and open decisions

| Item | Evidence available now | What remains to verify |
| --- | --- | --- |
| OpenShift / OpenShift AI | Red Hat's 3.x matrix lists AI 3.5 with OpenShift 4.22 | Inspect actual operator and component versions separately; operator health does not establish serving readiness |
| GPU Operator | Current research is recorded in the [GPU assessment](00-gpu-compatibility.md) | Match catalog bundle, hardware, driver, kernel, module type, and dependencies before selection |
| RTX 4070 | CUDA-capable; viable lab candidate, outside the reviewed GPU Operator and Red Hat AI Inference hardware lists | Exact installed hardware, driver/container operation, and inference test results |
| H100 | Listed in NVIDIA GPU and MIG documentation | Exact customer variant and complete supported platform/runtime combination; no customer configuration is validated yet |
| Serving runtime | The reference lab now uses the pinned Red Hat vLLM image in Stage 4 | On another environment, inspect installed AI components/APIs, supported image/version, GPU architecture, model format and quantization |
| Storage | A default class is reported | Class, provisioner, topology, binding mode, and later PVC provisioning and mount test on relevant nodes |

The OpenShift AI Operator does not itself establish NVIDIA driver readiness. Node Feature Discovery labels hardware capabilities. The GPU device plugin exposes GPU resources that Kubernetes can allocate. An absent `nvidia.com/gpu` value before enablement does not mean there is no physical GPU.

Current lab checkpoint: the collector has already run. Do not repeat the full inventory merely to continue the guide. Review the outstanding items in the lab record and repeat only checks affected by changes or stale evidence.

RTX 4070 does not support MIG. MIG partitions supported GPUs into isolated instances; time-slicing shares GPU execution and does not provide memory isolation. Neither will be enabled in this demo. See [MIG hardware](https://docs.nvidia.com/datacenter/tesla/mig-user-guide/supported-gpus.html) and [time-slicing behavior](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/24.9.2/gpu-sharing.html). The latter describes the distinction; it is not an operator-version recommendation.

## Console inspection — start here

1. Open the intended cluster's console. Go to **Administration → Cluster Settings**. Record the displayed release and any update or health issue. Do not change settings.
2. Open **Ecosystem → Installed Operators**, select all projects, and locate Red Hat OpenShift AI. Record its project, installed version, status, and subscription channel. Check whether Node Feature Discovery or NVIDIA GPU Operator is already present. OpenShift 4.22 documentation uses this navigation; if the console has different labels, record them and use the CLI inventory below rather than guessing.
3. Review the node and storage inventory through the CLI below. Additional console navigation will be matched to the verified cluster version in subsequent modules.

The console and CLI inspect overlapping information. These are read-only alternatives, not two installation procedures. Use the CLI collector to return precise evidence, especially for kernel versions and resource availability that console summaries may omit. No console method is assumed for inspecting physical GPUs before discovery is installed.

## CLI inventory

Confirm the current context before running the collector:

```bash
oc config current-context
oc whoami
```

Run from the repository root on your administration workstation:

```bash
bash checks/discover.sh
```

The script prints the exact command before each result. It collects:

- OpenShift client/server versions, an authorization check, and completed cluster release history.
- Cluster operator and machine configuration pool health.
- Node capacity, allocatable resources, operating system, kernel, labels, taints, and currently advertised GPU counts.
- StorageClasses, Container Storage Interface (CSI) drivers, and existing persistent volume claims (PVCs).
- Installed operator versions and subscription channels, available GPU/AI catalog package summaries, OpenShift AI custom resources, and serving API availability.

An operator custom resource is a configuration object that tells its operator what to manage. Its existence does not prove its status is healthy. Kubernetes allocatable capacity also does not equal unused capacity; current pod requests must be considered when placing the model.

The collector preserves errors and continues independent reads. Requests have a 30-second timeout. A failed read produces a nonzero script exit status after independent reads finish; authentication or API-discovery failure stops collection. Optional APIs that are not served are recorded as absent, not counted as failed reads. Exit status zero means collection succeeded, not that cluster health or compatibility passed. The authorization check uses an access review and does not change permissions.

Copied operator records are excluded using the observed `olm.copiedFrom` label so they are not mistaken for additional installations. The collector does not request Secrets or kubeconfig contents. Review outputs before sharing; hostnames, usernames, internal addresses, labels, and storage parameters may identify your lab. Use consistent aliases if redacting node names.

### Physical GPU evidence, if existing host access is available

Use an existing host console or SSH session on each GPU worker. Do not enable SSH or install packages for this stage. Map the host to its Kubernetes node name from the earlier inventory.

```bash
hostname
lspci -Dnnk -d 10de:
```

Record each NVIDIA VGA, 3D, or display-controller PCI address and device ID. NVIDIA audio functions are not additional GPUs. This command also shows the active kernel driver when present. If `lspci` is unavailable, preserve that result; do not install it during this stage.

If the NVIDIA driver and its utility are already present, run:

```bash
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi --query-gpu=name,pci.bus_id,memory.total,memory.used,driver_version --format=csv
else
  printf '%s\n' 'nvidia-smi is not available; driver and VRAM verification remain pending.'
fi
```

An unavailable or failed `nvidia-smi` is evidence to investigate, not proof of absent hardware. If you have no existing host access, report that fact. We will keep exact physical inventory pending and address it in GPU enablement. Do not treat `oc debug node` as read-only API discovery: it creates a privileged workload. When hands-on diagnostics are authorized, follow the separate [hardware discovery supplement](00-hardware-discovery.md).

If an existing SSH path fails host-key verification, stop and verify the host identity through a trusted console or administrator process. Do not bypass checking to finish the inventory. Host access is separate from cluster-admin API access.

## Expected results and verification

| Check | Expected evidence | If different |
| --- | --- | --- |
| Release | Reported version matches completed history; cluster is not mid-update | Return actual version and conditions; do not change versions |
| Cluster operators | Available=True, Degraded=False; unexpected Progressing states investigated | Diagnose affected operator before dependent work |
| Machine configuration pools | Updated=True, Updating=False, Degraded=False | Investigate pool status before driver installation |
| Nodes | Ready; capacities and placement match actual hardware | Resolve NotReady nodes; distinguish capacity from allocatable and free resources |
| AI installation | Installed operator version and healthy status; custom resources reflect actual state | Missing configuration is an input to OAI-02, not a reason to create defaults now |
| GPU inventory | Physical evidence maps devices to workers, or pending facts are explicit | Empty GPU resources can be expected before device-plugin setup |
| Storage | Default annotation, provisioner, topology, reclaim policy, binding mode recorded | A class alone does not prove storage is usable; validate in OAI-03 |

`WaitForFirstConsumer` means a PVC can stay Pending until a consuming pod is scheduled. Existing Bound PVCs show past provisioning only. They do not prove that the intended storage can attach to the GPU workers or satisfy the new model's needs.

## Common failures and troubleshooting

- Wrong cluster or expired login: stop and authenticate with your existing method. Do not share tokens or kubeconfig files.
- `oc` missing: use your existing OpenShift administration workstation or obtain the matching client from the cluster's CLI download page. Return the issue if that is not available.
- `Forbidden`: return the failing command and error. Do not add privileges speculatively. The discovery role is cluster-admin; later project-role checks are separate.
- Operator API not served: report it. The collector checks API availability and also reads OLM v1 ClusterExtensions when present; missing legacy APIs do not establish that an operator is absent.
- Empty catalog or package results: preserve the output. Catalog health and package availability must be resolved before selecting an installation channel.
- Missing GPU labels/resources: expected if discovery and the device plugin are absent. Confirm hardware using existing host access when possible.
- Degraded cluster or an update in progress: return the affected status. We will troubleshoot before operator installation.

## Completion checkpoint — stop here

Return:

1. Collector output, including errors, with sensitive environment identifiers redacted as needed.
2. Which node names correspond to the two GPU workers.
3. Per-worker `lspci` and optional `nvidia-smi` output, or a note that host access is unavailable.
4. Any difference between console-reported AI version/status and CLI output.

The stage is complete only after the inventory and uncertainties are reviewed. Unknowns must be recorded explicitly; later stages cannot treat them as passed checks. No need to repeat hardware or sizing answers already provided.

## Cleanup and rollback

The API inventory creates no cluster resources and requires no cluster rollback. The hardware supplement creates temporary diagnostic resources and requires its own cleanup verification. If you saved raw output locally, keep it outside Git or under the ignored `inventory/` directory.

## Official sources

- [Red Hat OpenShift AI 3.x supported configurations](https://access.redhat.com/articles/rhoai-supported-configs-3.x)
- [OpenShift AI 3.5 documentation](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5)
- [GPU compatibility assessment and current sources](00-gpu-compatibility.md)
- [OpenShift 4.22 console overview](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/web_console/web-console-overview)
- [OpenShift 4.22 operator user tasks](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/operators/user-tasks)
- [OpenShift 4.22 storage APIs](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html-single/storage_apis/index)
