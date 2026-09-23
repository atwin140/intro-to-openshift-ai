# OAI-07B — Second deployment, sharing, and H100 (optional)

Applicability: planning module. RTX 4070 whole-GPU operation is locally tested; H100 and sharing changes are not. Roles: cluster-admin for hardware, drivers, sharing/MIG, and placement preparation; project administrator for model deployment after handoff. Prerequisites: verified customer platform/support matrix, exact H100 variant, spare capacity, and a maintenance/rollback plan.

## Objective and current placement

Compare independent deployments with GPU sharing. The separate [image-generation lab](../../image-generation/README.md) now uses gpu-worker-02 with one whole GPU; command-helper uses gpu-worker-01. That extension has its own [validation](../../image-generation/VALIDATION.md). Do not assume the second GPU is free. Do not relocate the chat onto it or start a new whole-GPU test there while the image model holds its allocation.

## Planned procedure and verification

1. Inventory available GPU resources and running allocations. Capacity is not free capacity.
2. For another whole-GPU deployment, use distinct model/service names and explicit placement, storage, and security configuration; budget one GPU per replica.
3. For H100, re-check supported OpenShift, OpenShift AI, GPU Operator, driver, runtime, precision, and model combinations. Keep hardware-specific changes in a separate customer overlay; do not copy the GeForce driver/lab assumptions blindly.
4. H100 supports MIG on supported variants. Select instance profiles only after workload memory testing. RTX 4070 does not support MIG.
5. Time-slicing shares execution access and does not isolate GPU memory. It does not turn one 12 GB GPU into multiple independent 12 GB devices. It remains disabled in the current lab.
6. Any sharing/MIG exercise needs its own maintenance window, manifests, resource-name discovery, placement checks, and interference/OOM tests before it is called complete.

There are no executable H100 or sharing overlays yet. Console fields and exact CLI resources will be taken from the verified installed APIs at that stage. No current ClusterPolicy should be changed by this module.

## Failures, checkpoint, and rollback

Pending replicas may indicate allocated GPUs, mismatched resource names, or storage topology—not a missing driver. Resolve the actual cause. Checkpoint requires measured memory/concurrency and recovery on the target hardware; current status is unvalidated. Restore the recorded whole-GPU policy and scheduling configuration using the target version's documented maintenance procedure; device repartitioning can disrupt workloads. Do not attempt it as a troubleshooting shortcut.

Sources: [NVIDIA MIG hardware](https://docs.nvidia.com/datacenter/tesla/mig-user-guide/supported-gpus.html), [GPU time-slicing](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/gpu-sharing.html), [GPU Operator platform support](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/platform-support.html).
