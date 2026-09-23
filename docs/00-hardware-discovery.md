# OAI-00-H — Inspect GPU worker hardware through the cluster API

Version applicability: OpenShift 4.22; procedure executed in this lab on 2026-09-22. This supplements [read-only discovery](00-discovery.md).

## Objective and purpose

Identify the NVIDIA devices visible to each GPU worker, current driver state, virtualization, and guest firmware interface. This avoids choosing a driver configuration from reported hardware alone.

## Required role and prerequisites

Cluster-admin, the intended authenticated cluster context, the repository, and authorization to create temporary privileged diagnostic pods are required. The lab owner authorized this hands-on step. The commands inside the pods only read host information. Creating a pod is still a cluster write; this is separate from read-only API discovery.

## Console and CLI instructions

Use the console to inspect the worker node status. No equivalent console-only hardware inventory procedure is assumed. Run the following from the repository root in Bash. Substitute each verified GPU worker name in turn; do not use an arbitrary node.

```bash
oc config current-context
oc whoami --show-server
oc whoami
gpu_worker='<verified-gpu-worker-name>'
tools_image=$(oc get istag tools:latest -n openshift \
  -o jsonpath='{.image.dockerImageReference}')
printf 'Resolved diagnostic image: %s\n' "$tools_image"
case "$tools_image" in
  *@sha256:*) ;;
  *) printf 'Expected a digest-pinned tools image; stop.\n' >&2; exit 1 ;;
esac
bash -n checks/host-inventory.sh
oc debug "node/$gpu_worker" --image="$tools_image" -- \
  chroot /host /bin/bash -c "$(cat checks/host-inventory.sh)"
```

Record the resolved digest and output in ignored local inventory. The lab used `quay.io/openshift-release-dev/ocp-v4.0-art-dev@sha256:392e9833715141f9fc2f4dbe6f622a950755fd2ae5e78fd31c78f558ea3e74b5`. Resolve the image from the target cluster for a different release. No host software is installed, and no SSH trust settings are changed. `oc debug` explicitly places its privileged pod on the named node; it does not test normal GPU scheduling.

## Expected results and verification

- Count only NVIDIA display/3D controllers, not associated audio functions.
- Record node, PCI address, numeric device ID, and active driver. An identical PCI address on two virtual machines is local to each guest and does not establish physical host placement.
- `Kernel modules: nouveau` in `lspci` lists a possible driver. It does not mean that module is loaded. Check the active driver link and `/proc/modules` as the script does.
- `qemu` means virtualization was detected. GPU passthrough is an inference until the hypervisor configuration is inspected; do not describe the guest as bare metal or assume a vGPU configuration.
- Missing `nvidia-smi` before enablement leaves actual VRAM and CUDA operation pending for OAI-01.
- No EFI interface means guest UEFI Secure Boot is not applicable to this boot. It says nothing about the physical hypervisor's firmware settings.

After both runs:

```bash
oc get pods -A -l debug.openshift.io/managed-by=oc-debug
oc get nodes
oc get co
oc get mcp
```

Expect the diagnostic pods to be gone, nodes Ready, cluster operators Available=True/Progressing=False/Degraded=False, and machine configuration pools Updated=True/Updating=False/Degraded=False. Compare against the precheck. Record any temporary debug namespace named by the client and verify its removal too.

## Common failures and troubleshooting

- Image pull or pod startup failure: inspect that diagnostic pod's events. Do not switch to an unverified image or change host packages.
- `mokutil` reports EFI variables unsupported: inspect whether `/sys/firmware/efi` exists. The collector handles absent EFI as a recorded boot limitation; do not call Secure Boot verified or enabled.
- `Forbidden`: this step needs cluster-admin diagnostic access. It is not part of the later project-admin workflow.
- GPU absent or a driver query fails: preserve the failure. Investigate device assignment or driver state before claiming GPU readiness.
- Unknown SSH host keys: keep verification enabled. This API method is an alternative authorized access path, not an SSH bypass.

## Completion checkpoint

Stop after both workers have recorded device identities/counts, driver state, virtualization, firmware limitations, cleanup, and cluster health. GPU computation, memory measurement, and operator installation belong to OAI-01. Hypervisor configuration remains an explicit uncertainty when only guest evidence is available.

## Cleanup and rollback

`oc debug` normally deletes its pod when the command finishes, including a command failure. Verify deletion. If interrupted cleanup leaves resources, inspect and delete only the exact diagnostic pod and temporary namespace created by this run. Never bulk-delete all debug pods or namespaces; another administrator might be using them. No driver, label, taint, or persistent host configuration is changed by this procedure.

## Official sources

- [OpenShift 4.22 node diagnostics and host access](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/support/gathering-cluster-data)
- [NVIDIA GPU Operator deployment options and support matrix](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/26.7/platform-support.html)
