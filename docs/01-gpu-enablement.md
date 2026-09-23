# OAI-01 — Enable and test both GPUs

Applicability: OpenShift 4.22.13, NFD bundle `nfd.4.22.0-202609151747`, GPU Operator 26.7.0, and driver 595.91.07. Verified fields come from the installed custom resource definitions (CRDs) and bundle examples. RTX 4070 remains a lab configuration outside the reviewed vendor hardware support lists. See [support assessment](00-gpu-compatibility.md).

## Objective and prerequisites

Make each GPU available to normal Kubernetes scheduling, then prove that each can execute a CUDA calculation. CUDA is NVIDIA's GPU computation platform. Driver availability alone is not a computation test.

Required role: cluster-admin. Complete OAI-00, confirm both worker identities, and verify healthy cluster operators and machine configuration pools. Use the existing authenticated `oc` session from the repository root. This module is separate from the future project-admin workflow.

## Decisions and placement

- NFD scans nodes and publishes hardware labels. The NVIDIA vendor label is `feature.node.kubernetes.io/pci-10de.present=true`; it must identify exactly the intended GPU workers before applying the driver policy.
- The GPU Operator places its GPU components using discovered labels. No manual GPU labels or node taints are added. Existing service workloads are not drained.
- The lab uses open kernel modules and OpenShift Driver Toolkit. The selected driver image digest was inspected and reports version 595.91.07; it is not an assumed tag match.
- The ClusterPolicy sets MIG strategy `none` and disables MIG Manager. No time-slicing configuration is supplied. vGPU, VFIO, sandbox, and confidential-computing managers are disabled. Virtualized workers running containers do not require these components.
- Both subscriptions use Manual approval. `startingCSV` selects the initial bundle; it is not a permanent version lock. Review every later install plan before approving it. Driver automatic upgrades are disabled for this initial lab.
- Validation jobs request one whole GPU each. Each lab patch selects one existing `kubernetes.io/hostname` label, so the scheduler must allocate a GPU on that worker. No `nodeName` bypass is used. The temporary test service account has no role bindings or API token mount.

## Console first — inspect and understand

1. Open **Ecosystem → Installed Operators**. Inspect the NFD and NVIDIA GPU operators after the CLI installation below. Before installation, they are available through **Ecosystem → System Catalog**.
2. In each operator's project, inspect the installed bundle and its status. Manual approval means a resolved install plan waits for an administrator.
3. Use **Compute → Nodes**, select each GPU worker, and inspect its labels and GPU capacity after configuration.
4. Open the NVIDIA operator's **ClusterPolicy** tab to inspect `gpu-cluster-policy`. Expect `ready` only after its required components initialize.

The web-console install forms are an alternative installation method. This lab uses the complete Kustomize files below as the source of truth, so do not install a second copy through the forms. Console views are used for inspection. Where a console differs, use the CLI evidence instead of guessing a label.

## CLI — install operators

```bash
oc config current-context
oc whoami --show-server
oc get nodes
oc get co
oc get mcp
oc kustomize platform/gpu/operators/overlays/lab
oc apply -k platform/gpu/operators/overlays/lab
oc get installplan -n openshift-nfd
oc get installplan -n nvidia-gpu-operator
```

Wait for each subscription to resolve. Obtain its exact plan name, inspect the proposed CSV list, and approve only the expected initial bundle. Do not approve every plan in a namespace. Substitute the observed names in these commands:

```bash
oc get installplan <nfd-plan> -n openshift-nfd -o yaml
oc get installplan <gpu-plan> -n nvidia-gpu-operator -o yaml
oc patch installplan <nfd-plan> -n openshift-nfd --type=merge -p '{"spec":{"approved":true}}'
oc patch installplan <gpu-plan> -n nvidia-gpu-operator --type=merge -p '{"spec":{"approved":true}}'
oc get csv -n openshift-nfd -l '!olm.copiedFrom'
oc get csv -n nvidia-gpu-operator -l '!olm.copiedFrom'
```

Both CSVs must reach `Succeeded` before their configuration is applied. The selected bundle names are listed at the top of this module. Catalog contents can change; reassess a different bundle rather than silently substituting it.

## CLI — discover hardware, then install the driver

```bash
oc apply --dry-run=server -k platform/gpu/discovery/overlays/lab
oc apply -k platform/gpu/discovery/overlays/lab
oc get pods -n openshift-nfd
oc get nodes -l feature.node.kubernetes.io/pci-10de.present=true -o name
```

Wait for NFD pods to become Ready. Confirm the NVIDIA label matches only the intended GPU workers. Then:

```bash
oc apply --dry-run=server -k platform/gpu/configuration/overlays/lab
oc apply -k platform/gpu/configuration/overlays/lab
oc get clusterpolicy gpu-cluster-policy
oc get pods,daemonsets -n nvidia-gpu-operator -o wide
```

Initial driver compilation and image pulls can take several minutes. Inspect the driver pod's two containers separately; use the actual pod name returned above:

```bash
oc logs -n nvidia-gpu-operator <driver-pod> -c openshift-driver-toolkit-ctr --tail=80
oc logs -n nvidia-gpu-operator <driver-pod> -c nvidia-driver-ctr --tail=80
```

For each worker's driver pod:

```bash
oc exec -n nvidia-gpu-operator <driver-pod> -c nvidia-driver-ctr -- \
  nvidia-smi --query-gpu=name,uuid,pci.bus_id,memory.total,memory.used,driver_version --format=csv
oc exec -n nvidia-gpu-operator <driver-pod> -c nvidia-driver-ctr -- \
  cat /proc/driver/nvidia/version
```

Record actual memory in MiB and confirm the kernel-module type. GPU memory measured here is a baseline; model peak memory and headroom are separate OAI-04 checks.

## CLI — compute on each worker

On a fresh lab, these tests run before model deployment. On the current lab both GPUs are allocated: command-helper uses gpu-worker-01 and the separate image generator uses gpu-worker-02. Re-running whole-GPU test Jobs will leave them Pending unless the corresponding model is deliberately stopped in a maintenance window. Do not interrupt the working demo merely to replay completed validation.

Proceed only when driver readiness and one allocatable `nvidia.com/gpu` per worker are confirmed. Inspect each node with `oc describe node <worker>`.

```bash
oc kustomize platform/gpu/validation/overlays/lab
oc apply -k platform/gpu/validation/overlays/lab
oc get jobs,pods -n intro-ai-gpu-checks -o wide
oc logs -n intro-ai-gpu-checks job/cuda-vectoradd-01
oc logs -n intro-ai-gpu-checks job/cuda-vectoradd-02
```

Expect both Jobs to complete, their pods to have run on different intended workers, and both logs to report `Test PASSED`. A failed job has no automatic retries; preserve logs, fix the cause, then delete and recreate only that test job. The lab overlay pins the verified linux/amd64 sample image digest. The base alone does not constrain node placement; deploy the lab overlay.

## Common failures and troubleshooting

- Subscription waiting: inspect its conditions and catalog bundle-unpack job. A missing install plan immediately after creation is not itself a failure.
- Image metadata is multi-architecture: use `oc image info --filter-by-os=linux/amd64` before recording the digest for these amd64 workers.
- Driver build/load failure: inspect both containers, kernel/toolkit match, module type, and guest device assignment. Do not run a standalone driver installer on CoreOS.
- `lspci` lists nouveau: that is a possible module, not proof it is loaded. Check `/proc/modules` and the active driver.
- Pending test: inspect scheduling events, node selector, GPU capacity, and existing allocations. Do not remove the GPU request to make it schedule.
- Exporter startup connection failures: if its hostengine is still pulling or starting, inspect those events and allow dependency startup. Confirm subsequent readiness; do not count an early connection failure as a permanent hardware failure.
- DCGM errors on GeForce: preserve and assess the specific error. Do not disable monitoring to conceal an unrelated driver failure.
- Admission failure: preserve the security-context error. Do not grant the test account privileged access by default.

## Completion checkpoint

Record bundle/image versions, policy state, per-node GPU resource count, driver/module version, device memory, both computation results, and final cluster health. Confirm no sharing resources or inflated GPU counts. Stop before OAI-02. Local execution evidence belongs in lab progress (private local evidence; excluded from the public repository), not in these reusable expected results.

## Cleanup and rollback

After saving validation logs, remove the dedicated test namespace, account, and jobs with `oc delete -k platform/gpu/validation/overlays/lab`. This releases the test GPU allocations. Keep the operators and policy for the next stage.

Full GPU removal is a separate administrator action after GPU workloads stop. Remove the ClusterPolicy first, inspect operator-managed cleanup, then remove the subscriptions/CSVs and NFD instance/operator using the vendor cleanup procedures. Do not use a broad delete of the entire platform tree as a rollback: operator removal is not proof that loaded host modules or runtime configuration have been reverted. Do not delete CRDs shared with other installations. Record any required node maintenance before carrying it out.

## Sources

- [NVIDIA OpenShift installation, verification, and CUDA sample](https://docs.nvidia.com/datacenter/cloud-native/openshift/latest/install-gpu-ocp.html)
- [Red Hat NFD operator for OpenShift 4.22](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/specialized_hardware_and_driver_enablement/psap-node-feature-discovery-operator)
- [GPU Operator 26.7 configuration](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/26.7/getting-started.html)
- [GPU Operator platform and driver matrix](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/26.7/platform-support.html)
- [NVIDIA OpenShift cleanup](https://docs.nvidia.com/datacenter/cloud-native/openshift/latest/clean-up.html)
