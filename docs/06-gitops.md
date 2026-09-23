# OAI-06 — Prepare an existing Argo CD handoff

Applicability: the verified OpenShift 4.22.13 / OpenShift AI 3.5.1 lab manifests. Argo CD instructions use current upstream documentation; the installed GitOps version, policies, and synchronization behavior have not been validated here. This module prepares adoption, not an installed or tested GitOps service.

## Objective, roles, and prerequisites

Keep the same Kustomize source for manual deployment and eventual GitOps reconciliation. The project administrator prepares and reviews repository content. An Argo CD administrator owns repository/cluster registration, AppProject policy, controller permissions, and Application creation rights. Being admin in intro-openshift-ai does not grant access to the Argo CD control namespace.

Complete platform/project setup and the model download before the first sync. A new PVC without downloaded weights cannot start this deployment. Retain the Stage 4 quality limitation. Resolve cluster health issues before claiming a clean handoff.

## Project administrator: prepare the repository

From a working copy of the guide, run:

```bash
python3 checks/review-walkthrough.py
oc apply --dry-run=server -k deploy/overlays/lab
```

Copy the directory into your chosen Git working directory. Exclude local inventory and progress notes, outputs, credentials, and downloaded artifacts. Example with an explicit destination placeholder:

```bash
rsync -a --exclude='.git/' --exclude='notes/' --exclude='inventory/' \
  --exclude='secrets/' --exclude='.env*' --exclude='*.key' \
  --exclude='*.pem' --exclude='*.kubeconfig' --exclude='kubeconfig' \
  ./ /ABSOLUTE/PATH/TO/NEW/REPOSITORY/
```

Replace the destination before running. Inspect the copied files; ignore patterns are not a secret scanner. Initialize or use the intended repository, inspect `git status --short` and `git diff --cached` before committing, and publish only to the approved destination. Never store Git credentials or cluster access tokens in Application YAML. No remote repository or branch is assumed.

The combined overlay is `deploy/overlays/lab`. Stage 4 alone is `deploy/overlays/lab-model`. Choose one owner for shared model resources; do not create two Applications managing both overlays at once. Console YAML import cannot preserve the Kustomize source structure.

## Argo CD administrator: bootstrap and review

1. Record the installed Argo CD/OpenShift GitOps version and verify its Kustomize rendering supports these files.
2. Register the approved Git repository and destination cluster through the existing installation's credential management. Do not commit their Secrets.
3. Create or select an AppProject restricted to that repository and destination namespace. Permit the needed namespaced kinds: ServiceAccount, ConfigMap, Service, PersistentVolumeClaim, Deployment, NetworkPolicy, Route, InferenceService, and ServingRuntime. No cluster-scoped resources are required by the application overlay. Confirm controller-managed child resources and InferenceService health reporting behave correctly in this installation.
4. Give the application controller the required read/watch and reconcile permissions for those resources in intro-openshift-ai. AppProject policy is separate from Kubernetes RBAC. Review any OpenShift GitOps managed-namespace mechanism against the installed version. Do not grant the project user cluster-admin.
5. Replace all placeholders in `gitops/application.yaml`. Use a reviewed immutable commit initially. For an in-cluster Argo CD managing this same cluster, the registered destination may be `https://kubernetes.default.svc`; verify registration rather than assuming it.
6. Create the Application with the authorized Argo CD account. Inspect its rendered diff in the Argo CD UI before the first manual sync. Do not enable pruning or automated sync for initial adoption. Existing generated Deployments/Routes belong to KServe; do not commit copied children into Git.

The example deliberately omits automated sync, namespace creation, and a cascading-deletion finalizer. This does not prevent an operator from manually deleting a PVC or choosing prune: inspect every deletion plan. The storage class uses Delete reclaim policy. Establish backup/restore and resource retention policies before enabling automated deletion.

## Verification, failures, and checkpoint

Expected after a separately authorized sync: the Application reports its reviewed commit; resources reconcile; model and UI probes pass; claim data remains available. Compare the Argo-rendered result to `oc kustomize deploy/overlays/lab`. Repeat `checks/chatbot.py` and `checks/model-route.py`. Record actual identity, result, and limitations.

If sync is Forbidden, distinguish AppProject restrictions, Argo user authorization, and controller Kubernetes permissions. A missing CRD is platform preparation, not a reason to skip validation. Model load failure on an empty claim requires the pinned download stage. An Unknown custom-resource health status requires version-specific health assessment, not declaring the service unhealthy from that label alone.

Completion: repository render/dry-run passes, bootstrap owner and placeholders are resolved, manual sync passes, and deletion/restore behavior is reviewed. Until an actual Argo sync is performed, mark adoption untested. No GitOps installation is required for the working manual demo.

## Cleanup and rollback

Stop reconciliation before manual rollback. Restore a previously reviewed commit and inspect/sync its diff. If retiring the Application, use the installed Argo CD procedure for non-cascading removal and verify that model resources and PVCs are retained. Do not delete the project or data claim as Application cleanup. These deletion procedures are documented, not executed in this review.

## Sources

- [Argo CD Kustomize](https://argo-cd.readthedocs.io/en/stable/user-guide/kustomize/)
- [AppProject boundaries](https://argo-cd.readthedocs.io/en/stable/user-guide/projects/)
- [Sync and resource-retention options](https://argo-cd.readthedocs.io/en/stable/user-guide/sync-options/)
