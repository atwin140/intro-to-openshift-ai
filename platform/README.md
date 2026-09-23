# Cluster-admin preparation

Follow [OAI-01](../docs/01-gpu-enablement.md). These resources require cluster-admin and must not be included in the future project-admin application overlay.

Apply these independent Kustomize roots in sequence, verifying each prerequisite:

1. `gpu/operators/overlays/lab`: namespaces, OperatorGroups, manually approved subscriptions.
2. `gpu/discovery/overlays/lab`: NFD configuration after its API and operator are ready.
3. `gpu/configuration/overlays/lab`: whole-GPU ClusterPolicy after discovery identifies the intended nodes.
4. `gpu/validation/overlays/lab`: temporary computation jobs after GPUs are allocatable.

The `.json` resources are complete Kubernetes manifests accepted by Kustomize. Each root has a reusable base and lab overlay. Separating the roots prevents applying custom resources before their operators and APIs exist. There is intentionally no parent kustomization that installs all stages at once.

Operator bundle choices, driver digest/module type, test-image digest, and test node names are explicit in the lab overlays. The base targets these API versions, not every possible OpenShift/GPU Operator version. Future H100 settings require separate validation and overlays.

The test namespace `intro-ai-gpu-checks` is dedicated to temporary administrator tests. Its account has no additional permissions and does not mount an API token. Delete that overlay after preserving evidence. Full operator cleanup requires the staged procedure in OAI-01.

## OpenShift AI preparation

After the OAI-01 checkpoint, follow [OAI-02](../docs/02-openshift-ai.md):

1. Apply `oc apply -k platform/ai/overlays/lab` to create the new-installation DataScienceCluster with dashboard and KServe Managed, other components Removed.
2. Wait for the dashboard API/object, then apply `oc apply -k platform/ai-dashboard/overlays/lab` to enable its KServe and standard-deployment features.
3. Verify component readiness, serving APIs, effective configuration, runtime templates, and the existing gateway.

Do not apply the new-installation component profile over an unrelated existing DataScienceCluster. The pre-existing DSCI, gateway, cert-manager, and authentication settings are prerequisites inspected in the guide, not recreated by these overlays. Applying these files does not deploy a model.

## Project and storage preparation

Follow [OAI-03](../docs/03-project-handoff.md). `project/overlays/lab` creates only the demo namespace. `storage-check/overlays/lab` provisions a disposable PVC; run its `write/overlays/lab` and `read/overlays/lab` pod overlays sequentially, deleting the first pod before the second. The lab security patches contain the observed project filesystem group and must be reviewed if the namespace is recreated.

`project-access/base` contains a namespace-scoped built-in admin RoleBinding with no subjects. The base alone grants no access. The lab overlay binds the confirmed user `ai-user` and has been applied. Actual-login checks are in `checks/project-permissions.py` and `checks/project-access`; they are not substitutes for identifying and authenticating the intended user.
