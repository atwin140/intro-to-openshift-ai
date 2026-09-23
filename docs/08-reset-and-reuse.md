# OAI-08 — Reset and reuse a dedicated lab

Applicability: the repository's OpenShift 4.22 / OpenShift AI 3.5 / GPU Operator 26.7 resource layout. Reinspect versions and ownership on every cluster. Script removal has not been executed against the live reference demo. Preview and mocked safety tests have passed; they do not establish successful platform uninstallation.

## Objective and reset choice

Prepare a lab for another participant without confusing an application reset with a clean operating-system installation. Required role: cluster administrator using an existing authenticated `oc` context. Requirements: Python 3, `oc`, backup decisions made, and no other users working in the selected scope.

For two separate clusters, use one physical GPU worker with one RTX 4070 in each cluster. Each cluster needs its own control plane, networking/DNS, storage provisioning and platform operators. The existing overlays refer to reference's two workers and are not yet portable one-worker cluster profiles. Adapt placement, hostname, API endpoint, storage class, Route settings, participant identity and namespace security allocation separately. A physical GPU worker cannot be an active member of both clusters at once. The full-size chat model and image generator cannot both reserve that one whole GPU simultaneously; omit the optional image exercise or run it at a separate checkpoint.

| Training goal | Reset method | Next starting point |
| --- | --- | --- |
| Repeat project handoff, model deployment and chat UI | Project reset; retain drivers and AI platform | Stage 3 |
| Rehearse AI component configuration | Project reset, then AI stage reset | Stage 2 |
| Rehearse operator installation on the existing OS | Project, AI, then GPU reset; inspect remaining host/operator state | Stage 0/1, with residue documented |
| Start every group from a clean driver/operator baseline | Reprovision the dedicated cluster and GPU worker OS from repeatable installation inputs | Stage 0 |

We recommend project reset for routine participant turnover, and reprovisioning for a full administrator course that includes driver installation. Platform teardown cannot guarantee the original node state. Rebuilding only virtual control-plane machines while preserving modified physical workers is not a clean baseline. Do not use independent live VM snapshots as a cluster-reset procedure; preserve a supported, coherent recovery or provisioning process and account for external storage.

## Scope and data loss

[reset-lab.py](../scripts/reset-lab.py) has three separately invoked stages. It defaults to read-only preview, freezes the selected context, verifies the ClusterVersion cluster ID and requires cluster-admin access. Execution requires both an exact stage confirmation and an acknowledgement of dedicated scope/data loss/paused external reconciliation. It never reads Secret contents or exports kubeconfig, tokens, private keys, or model logs. Namespace deletion still deletes the Secrets inside that namespace.

- `project`: removes all InferenceServices and then the entire `intro-openshift-ai` namespace, including the chatbot, image generator, model downloads, participant additions, PVCs, Routes, service accounts and role bindings. Also removes the temporary `intro-ai-gpu-checks` namespace if present. Removes the exact lab model-auth ClusterRoleBinding only after verifying its expected role and subject. Existing OpenShift user accounts are retained.
- `ai`: requires the project to be absent and blocks if any InferenceService remains elsewhere. Sets dashboard/KServe to Removed, waits for their component CRs to disappear, then removes the lab-created `default-dsc`. Blocks if other AI components are enabled. Retains the pre-existing OpenShift AI operator, DSCI, gateway, identity configuration and cert-manager.
- `gpu`: requires project and DataScienceCluster removal. Blocks remaining GPU-requesting workloads and unexpected operator/configuration instances. Removes the lab ClusterPolicy, waits for GPU DaemonSet cleanup, then removes NFD configuration, the two subscriptions, their installed CSVs, and their dedicated namespaces. Leaves CRDs, possible cluster-scoped OLM residue, node labels, loaded modules and runtime residue for inspection. It does not reboot or drain nodes, remove finalizers, or claim a factory reset.

Both current model PVCs use Delete reclaim policy. Deleting the project is expected to delete the downloaded weights and backing volumes. The script waits for recorded Delete-policy PVs to disappear but cannot prove storage-array erasure. Retain-policy volumes are reported for manual disposition; it never directly deletes PVs. Save any data you need through a separate approved backup process first. Deletion cannot be undone by reapplying manifests; weights must be downloaded again and other data restored from backups.

## Console preparation and inspection

1. Inspect the intended cluster address and selected project before starting.
2. Review workloads, storage claims and participant changes in the demo project. Include the separate image generator.
3. Inspect installed operators and existing AI workloads in other projects before a platform reset.
4. If GitOps was adopted, the Argo CD administrator must resolve Application ownership and stop reconciliation first. The script blocks discovered Applications targeting lab namespaces, even with auto-sync disabled. Remote controllers, Applications without a destination namespace, ApplicationSets and other automation cannot be exhaustively detected. Do not simply force past an ownership problem.
5. Use the CLI below for guarded execution. Console deletion is possible for individual objects but does not provide this script's checks or staged checkpoints.

## CLI — select one cluster and preview

Run from the repository root. Keep each cluster's authenticated context separate. Do not put credentials in a script or shell argument.

```bash
oc config get-contexts
oc --context='<existing-admin-context>' whoami --show-server
oc --context='<existing-admin-context>' get clusterversion version \
  -o jsonpath='{.spec.clusterID}{"\n"}'
```

Independently confirm the displayed API and cluster identity against the intended lab's inventory. Then use those exact values; do not automatically populate the expected ID from whichever cluster happens to be active.

```bash
python3 scripts/reset-lab.py \
  --context='<existing-admin-context>' \
  --expected-cluster-id='<verified-cluster-uuid>' \
  --stage project
```

Expected: read-only preview names the API, cluster ID, namespaces, models, PV names and reclaim policies. Nothing is deleted. Review all scope before execution. The documented namespace names are fixed; this is not an arbitrary namespace-deletion tool.

## CLI — execute only the reviewed stage

The following command is destructive. It includes the optional image generator because that workload lives in the same project.

```bash
python3 scripts/reset-lab.py \
  --context='<existing-admin-context>' \
  --expected-cluster-id='<verified-cluster-uuid>' \
  --stage project --execute --confirm RESET-PROJECT --ack-dedicated-lab
```

Expected: the project and temporary test namespace disappear, their serving workloads terminate, and recorded Delete-policy PVs disappear. Inspect storage-provider state separately. The GPU and AI operators remain available. Stop here for routine participant turnover.

Only for a reviewed dedicated-platform reset, preview and then execute each next stage independently:

```bash
python3 scripts/reset-lab.py --context='<existing-admin-context>' \
  --expected-cluster-id='<verified-cluster-uuid>' --stage ai
python3 scripts/reset-lab.py --context='<existing-admin-context>' \
  --expected-cluster-id='<verified-cluster-uuid>' --stage ai \
  --execute --confirm RESET-AI --ack-dedicated-lab

# Inspect the AI-removal checkpoint before the GPU stage.
python3 scripts/reset-lab.py --context='<existing-admin-context>' \
  --expected-cluster-id='<verified-cluster-uuid>' --stage gpu
python3 scripts/reset-lab.py --context='<existing-admin-context>' \
  --expected-cluster-id='<verified-cluster-uuid>' --stage gpu \
  --execute --confirm RESET-GPU --ack-dedicated-lab
```

There is no unattended “delete everything” mode. Each stage stops on a failed API call or timeout. Default timeout is 300 seconds per operation; `--timeout` can be set from 30 to 1800 seconds. A failure can leave a partially completed reset; inspect it before rerunning. Already absent objects are tolerated when the relevant API remains installed.

## Verification and completion checkpoint

Use the same explicitly selected context for all checks:

```bash
oc --context='<existing-admin-context>' get ns intro-openshift-ai intro-ai-gpu-checks --ignore-not-found
oc --context='<existing-admin-context>' get pods -A -o wide
oc --context='<existing-admin-context>' get pv
oc --context='<existing-admin-context>' get co
oc --context='<existing-admin-context>' get mcp
```

After project reset, namespace lookup should return no objects. Inspect recorded PVs and serving resources, and confirm operators remain healthy. After AI/GPU reset, confirm the exact selected resources are absent; inspect remaining GPU capacity, node labels, cluster-scoped permissions and custom resource definitions. Do not count retained CRDs as a clean reinstall. No successful node/module removal has yet been demonstrated by this script.

Record cluster ID, stage, time, removed scope, retained data/resources, failures and observed health in private lab notes. Never record credentials. Existing Keycloak reachability/authentication degradation is a separate issue: resetting this lab will not fix an external identity provider.

## Recreate the participant project

Resume Stage 3 as cluster-admin after a project reset. Reapply the namespace overlay, verify the newly allocated security range, and update the lab patches before storage/download/model deployment:

```bash
oc --context='<existing-admin-context>' apply -k platform/project/overlays/lab
oc --context='<existing-admin-context>' get namespace intro-openshift-ai \
  -o jsonpath='{.metadata.annotations.openshift\.io/sa\.scc\.supplemental-groups}{"\n"}'
```

The old `fsGroup` value `1000000000` is not guaranteed after namespace recreation. Follow Stage 3's security-context validation and update these complete overlay files to the new allowed group before applying them:

- `platform/storage-check/write/overlays/lab/placement-security.json`
- `platform/storage-check/read/overlays/lab/placement-security.json`
- `deploy/download/overlays/lab/settings.yaml`
- `deploy/overlays/lab-model/model-settings-patch.yaml`
- Optional image exercise: `image-generation/download/job.json` and `image-generation/deploy/service.json`.

Select the next participant in the project-access overlay and repeat actual-user permission checks. Re-download model weights and follow the normal serving/UI checkpoints. A new project has a new UID and does not inherit old namespace-scoped access. For a one-GPU cluster, adjust Stage 1/3 validation to its single worker; do not run the two-node placement overlays unchanged.

## Common failures and recovery

- Output says `PREVIEW` / `Nothing changed`: no removal was attempted. Execution requires `--execute` as well as `--confirm` and `--ack-dedicated-lab`. The script now rejects confirmation flags without `--execute` and labels preview actions “Would delete.”

- Wrong ID or insufficient permissions: no mutations are allowed. Select the correct administrator context and verified cluster ID.
- Shared workloads or GitOps ownership: removal is blocked. Resolve scope with the owner rather than broadening deletion.
- Namespace, PVC or CR stuck Terminating: inspect events, finalizers, responsible controller health and storage connectivity. Restore the controller if needed. Do not strip finalizers or forcibly remove API definitions.
- Component/DaemonSet cleanup timeout: stop before uninstalling its controller; review the installed operator's version-specific behavior. This removal path is not yet live validated.
- Driver resources or node labels remain: this is not proof the GPU is clean. Use a reviewed node-maintenance procedure, or reprovision the dedicated lab for a clean driver-installation exercise.
- Recreated pod rejected or storage write denied: check the new namespace security range and worker/storage settings before changing permissions.

Rollback of the reset means reinstalling through the staged guide and restoring data from backups. This script does not implement cluster recovery or reverse a namespace deletion.

## Sources and validation boundary

[Red Hat AI 3.5 component management](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html/installing_and_uninstalling_openshift_ai_self-managed/installing-and-deploying-openshift-ai_install) documents Managed/Removed component states. This script uses that mechanism and retains infrastructure that predated the lab.

[NVIDIA OpenShift cleanup](https://docs.nvidia.com/datacenter/cloud-native/openshift/latest/clean-up.html) describes operator and ClusterPolicy CRD removal. This script deliberately retains shared API definitions and attempts custom-resource cleanup while controllers are present; it is a scoped lab teardown, not an implementation or validation of complete vendor uninstallation. For a guaranteed clean baseline, use dedicated-cluster reprovisioning.
