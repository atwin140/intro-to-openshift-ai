# OAI-03 — Prepare the project, storage, and project-admin handoff

Applicability: OpenShift 4.22.13, OpenShift AI 3.5.1, standard KServe serving. Tested lab storage: Synology CSI `csi.san.synology.com`, StorageClass `synology-iscsi-storage`. Vendor support for the entire lab configuration is not established by these functional tests.

## Objective and prerequisites

Provide a project in which the intended administrator can deploy the demo without cluster-admin. Verify that persistent storage can serve the model on either GPU worker. A persistent volume claim (PVC) requests storage; Bound means allocated, not necessarily writable by the application.

Required roles: cluster-admin for project creation and initial role assignment; then the actual project administrator for handoff verification. Complete OAI-02. Identify the handoff username before granting access. Never request or place login tokens in the guide, repository, or chat.

## Console inspection

Inspect the new project through the OpenShift console's project selector. Inspect its PVC and test pods, including their events and assigned nodes. The CLI below is the exact reproducible method; creating the same resources through the console is an alternative, not an additional step.

The OpenShift AI dashboard also requires its platform access rules to allow the user. The existing lab Auth allows `system:authenticated`. Do not grant the user OpenShift AI administrator membership merely to administer one project. Dashboard project visibility and actual authenticated access must be verified during handoff. Open **Projects**, select **Intro to OpenShift AI**, and confirm the user menu shows the intended identity. Expect the project overview and its **Deploy model** control. These labels were observed in the installed 3.5.1 dashboard.

## Cluster-admin: create the project

From the repository root:

```bash
oc config current-context
oc whoami --show-server
oc apply -k platform/project/overlays/lab
oc get project intro-openshift-ai
oc get namespace intro-openshift-ai -o jsonpath='{.metadata.annotations.openshift\.io/sa\.scc\.supplemental-groups}{"\n"}'
```

The namespace manifest includes `opendatahub.io/dashboard: 'true'` to identify the project for the AI dashboard. This label does not grant access; the namespace RoleBinding supplies access. The first manifest omitted this label; the corrected manifest was applied and dashboard visibility verified.

No quota or node taints are added. Project creation is separate from later project-scoped application overlays. The storage-test pod node selectors restrict each test to its intended GPU worker; they do not change node scheduling for other workloads.

## Cluster-admin: test storage sequentially

The lab test uses a disposable 1 GiB filesystem PVC. `ReadWriteOnce` permits read/write mounting on one node at a time, not one pod in all circumstances. Delete the first test pod before mounting on the second worker. This validates a single-replica relocation path, not simultaneous multi-node access or a storage performance benchmark.

The lab's allocated filesystem group is `1000000000`. It is recorded in each test overlay's `placement-security.json`. If the project is recreated or the guide is used elsewhere, read that project's allocation and update both patches before applying them. Never copy another project's group blindly.

The explicit `fsGroup` permits the non-root process to write to the iSCSI filesystem. No privileged init container, host package change, or broad filesystem permission change is needed. Pods disable service-account token mounting, drop capabilities, and prohibit privilege escalation.

```bash
oc apply -k platform/storage-check/overlays/lab
oc apply -k platform/storage-check/write/overlays/lab
oc wait --for=jsonpath='{.status.phase}'=Succeeded pod/storage-check-write -n intro-openshift-ai --timeout=60s
oc logs storage-check-write -n intro-openshift-ai
oc get pod storage-check-write -n intro-openshift-ai -o wide
```

Expect `WRITE-PASSED`, Bound PVC, and placement on the first worker. Save the logs and PVC/PV identity before cleanup. Then:

```bash
oc delete -k platform/storage-check/write/overlays/lab --wait=true
oc apply -k platform/storage-check/read/overlays/lab
oc wait --for=jsonpath='{.status.phase}'=Succeeded pod/storage-check-read -n intro-openshift-ai --timeout=60s
oc logs storage-check-read -n intro-openshift-ai
oc get pod storage-check-read -n intro-openshift-ai -o wide
```

Expect `READ-AND-WRITE-PASSED` on the second worker. The same PVC must be used for both operations. Preserve evidence, then remove only the temporary test resources:

```bash
oc delete -k platform/storage-check/read/overlays/lab --wait=true
oc delete -k platform/storage-check/overlays/lab --wait=true
```

The StorageClass reclaim policy is Delete. Verify that the recorded PV disappears. This cleanup is appropriate only for the disposable test claim; model data will need its own retention decision. A small-volume test does not establish capacity for every model size. Create the model PVC after the model's storage requirements are known.

## Cluster-admin: bind the intended identity

The reusable RoleBinding in `platform/project-access/base` references the built-in ClusterRole `admin` through a namespace-scoped binding. Its empty subjects list grants nobody access. Do not apply a placeholder username.

The confirmed lab identity is `ai-user`. The complete lab overlay adds that User subject:

```bash
oc apply --dry-run=server -k platform/project-access/overlays/lab
oc apply -k platform/project-access/overlays/lab
oc get rolebinding demo-project-admin -n intro-openshift-ai -o yaml
```

This binding is now applied in the lab. For reuse, change the subject in the lab overlay to the confirmed identity before applying. Administrator impersonation checks are preliminary evidence only; final acceptance requires the user's own authenticated session.

The installed built-in admin role already contains create/get/list/watch/patch/update/delete for `inferenceservices` and `servingruntimes`. This observation is not a substitute for testing the user's effective permissions, which can include additional group grants. Do not add a cluster-wide binding for the handoff.

## Project administrator: verify using the actual login

Use a separate locally authenticated session for the intended user. Keep the cluster-admin session available separately. Do not send credentials, and do not use `--as` impersonation for final acceptance.

```bash
oc whoami
python3 checks/project-permissions.py ai-user
oc apply -k checks/project-access
oc get configmap project-admin-handoff-check -n intro-openshift-ai
oc delete -k checks/project-access
```

The script checks the planned application's resource permissions and denies acceptance if the identity has the checked cluster-level powers. It checks deployment, route, storage, KServe, service-account, configuration, network-policy, and log permissions without reading Secret contents. The ConfigMap exercise proves actual Kustomize write/read/delete access under that login. Later application admission and runtime checks must still run under this same role.

If the user already has cluster-admin through another binding or group, adding a local admin binding does not remove that privilege. Choose an appropriate identity; do not remove unrelated access grants to manufacture a passing test.

## Common failures and troubleshooting

- PVC Pending: inspect claim events and CSI controller health. Both GPU workers must have the CSI node driver registered.
- Attach delay after relocation: inspect volume attachments and events; do not force-detach a volume still in use.
- Permission denied after mount: inspect the admitted pod security context and project group allocation. The first lab run lacked fsGroup under the selected AI SCC; explicitly setting the allocated group resolved it. Keep the failure evidence.
- Test pod Failed: inspect logs rather than retrying an unchanged manifest or counting a Bound claim as success.
- Project absent from the AI dashboard: confirm the intended browser identity, namespace dashboard label, and local RoleBinding. A CLI login does not change the browser session.
- Forbidden under project admin: identify the missing permission and move any cluster prerequisite to preparation. Do not use cluster-admin for the remainder and call the handoff complete.
- Login is unavailable: project/storage preparation can finish, but role acceptance remains blocked. No credentials should be shared to resolve it.

## Completion checkpoint

Require all of: project created, intended local admin binding applied, storage read/write verified on both workers, disposable resources cleaned up, and the actual non-cluster-admin login passing the permission and write/read/delete checks. Verify dashboard project access separately. Stop before OAI-04 if any required handoff check is pending.

Lab checkpoint (2026-09-22): passed using the actual `ai-user` login. The permission script passed, the ConfigMap apply/read/delete test passed and was cleaned up, and the dashboard project list and project overview were observed as `ai-user`. At that checkpoint, no model had been deployed. Subsequent model/application evidence is recorded in Stages 4 and 5.

## Rollback

Remove only the newly created `demo-project-admin` RoleBinding to revoke this grant; it does not revoke other grants. Delete the temporary test resources as above. Do not delete the project after it contains user/model data without reviewing all workloads and PVCs. No cluster-wide role, storage driver, or StorageClass was changed by this stage.

## Sources

- [OpenShift 4.22 authorization and security contexts](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html-single/authentication_and_authorization/index)
- [OpenShift 4.22 storage access modes](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html-single/storage/index)
- [Synology CSI upstream documentation](https://github.com/SynologyOpenSource/synology-csi)
- [OpenShift AI 3.5 user access](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html/managing_openshift_ai/managing-users-and-groups)

- [Red Hat namespace dashboard-label example](https://developers.redhat.com/articles/2026/09/11/bringing-custom-knowledge-agents-autorag) — only the namespace label is used here; AutoRAG is not enabled.
