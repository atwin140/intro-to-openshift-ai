# OAI-02 — Prepare OpenShift AI serving

Applicability: OpenShift 4.22.13, OpenShift AI operator 3.5.1, and the installed `datasciencecluster.opendatahub.io/v2` API. Sources and API schemas inspected on 2026-09-22.

## Objective and prerequisites

Enable the platform services that will manage the model deployment and provide the OpenShift AI administration dashboard. KServe is the controller that turns a model-serving specification into running Kubernetes resources. A ServingRuntime defines how to start the inference engine; an InferenceService describes a particular model deployment. Creating their APIs does not load a model or prove inference works.

Required role: cluster-admin. Complete OAI-01, confirm the intended authenticated cluster, and verify cluster health. The existing OpenShift AI operator must be ready. No DataScienceCluster existed before this lab step; if one exists in another environment, review and merge its configuration rather than applying this new-installation profile over it.

## Configuration and version decisions

The [complete platform overlay](../platform/ai/overlays/lab/kustomization.yaml) enables only `dashboard` and `kserve`. It explicitly sets all other top-level components to `Removed`, and disables optional NVIDIA NIM integration, model caching, and workload-variant autoscaling. `Managed` tells the operator to install and reconcile a component; `Removed` tells it not to install it or to remove it if present.

The installed v2 KServe schema states that only RawDeployment is supported. This standard deployment approach fits a single model replica that stays active. Do not copy older examples containing `serving`, `serviceMesh`, or `defaultDeploymentMode` into this v2 DataScienceCluster: those fields are not present in the installed schema. Some 3.5 documentation still discusses Knative; the actual installed API and resulting configuration must be checked before using that advice.

The existing DSCInitialization, authentication service, cert-manager, and OpenShift AI gateway are inspected and retained. This module does not recreate them or change login groups. The dashboard operator can deploy its own UI modules even when the corresponding optional backend component is Removed; a UI pod does not establish backend enablement. The later chatbot's anonymous Route is separate from the authenticated AI administration dashboard. No project-user access is claimed until OAI-03.

## Console instructions — inspect first

1. Open **Ecosystem → Installed Operators**, select the OpenShift AI operator, and inspect its installed version and status.
2. Open the **Data Science Cluster** tab. After applying the CLI overlay below, inspect `default-dsc`, its YAML, and readiness conditions.
3. Inspect the workloads in `redhat-ods-applications`. The exact names should come from the created resources, not from an older guide.
4. Once the dashboard is available, its documented serving controls are under **Settings → Cluster settings → General settings** and **Settings → Model resources and operations → Serving runtimes**. Inspection does not require creating a model. Access requires the corresponding OpenShift AI privileges.

Creating a DataScienceCluster through the console is an alternative to the CLI, not a second installation. This lab uses the repository as the source of truth. Apply its overlay once and use the console to inspect the result.

## CLI — precheck and apply

Run from the repository root:

```bash
oc config current-context
oc whoami --show-server
oc get csv -n redhat-ods-operator -l '!olm.copiedFrom'
oc get datascienceclusters
oc get dscinitializations
oc get gatewayconfigs
oc get co
oc get mcp
oc kustomize platform/ai/overlays/lab
oc apply --dry-run=server -k platform/ai/overlays/lab
oc apply -k platform/ai/overlays/lab
```

The server dry run verifies the installed schema and admission rules before mutation. It is not a readiness test. The operator creates and manages the component resources; do not edit their deployments directly.

After the dashboard creates its `ODHDashboardConfig` API and `odh-dashboard-config` object, apply the separate dashboard settings overlay. This explicitly enables KServe and standard-deployment features while preserving other existing settings:

```bash
oc apply --dry-run=server -k platform/ai-dashboard/overlays/lab
oc apply -k platform/ai-dashboard/overlays/lab
```

The first apply adopts these two user-configurable fields and can warn that the existing object lacks a last-applied annotation. That annotation is then created. Do not apply this overlay before the dashboard API exists. Runtime template disablement is inspected separately; the lab's templateDisablement list is empty.


## Expected results and verification

```bash
oc get datasciencecluster default-dsc -o yaml
oc get kserve default-kserve -o yaml
oc get dashboard default-dashboard -o yaml
oc get pods,deployments -n redhat-ods-applications
oc get crd inferenceservices.serving.kserve.io servingruntimes.serving.kserve.io
oc get configmap inferenceservice-config -n redhat-ods-applications -o yaml
oc get odhdashboardconfig odh-dashboard-config -n redhat-ods-applications -o yaml
oc get templates -n redhat-ods-applications
```

Use bounded readiness checks and inspect conditions if they time out:

```bash
oc wait --for=condition=Ready datasciencecluster/default-dsc --timeout=60s
```

Expected evidence:

- DataScienceCluster, dashboard, and KServe report Ready for the requested configuration.
- Required deployments have their requested number of available replicas; relevant webhook services have ready endpoints.
- InferenceService and ServingRuntime APIs are served, and the effective deployment configuration agrees with the selected standard deployment mode.
- The dashboard serving feature and relevant NVIDIA runtime template are inspected. A template's presence does not prove its image can run the selected model on an RTX 4070.
- Existing gateway and cluster health remain good. Disabled component conditions may be False with reason Removed; those are not installation failures.

The operator CSV version, DataScienceCluster release field, DSCInitialization release field, and individual runtime image versions are different observations. Record them separately. Never overwrite status fields to make versions appear to match.

## Common failures and troubleshooting

- Unknown field on dry run: stop and inspect `oc explain` or the installed CRD. Do not silently switch to an older API example.
- Webhook has no endpoints during initial startup: inspect the corresponding controller pod and service EndpointSlice. The lab recovered when the controller became ready; do not disable admission webhooks to bypass this check.
- Component not ready during startup: inspect that component's conditions, pod events, and image-pull progress. Do not enable unrelated components as a workaround.
- A dependency is unavailable: determine whether it is required for standard InferenceService serving or an optional distributed-serving feature before installing more operators.
- Dashboard permission denied: distinguish platform health from user authorization. Prepare the actual user's permissions in OAI-03; do not grant cluster-admin to solve project access.
- Gateway TLS error: verify the configured hostname and certificate chain. Do not bypass certificate verification.
- DSCI release metadata differs from the operator: preserve the discrepancy, inspect current reconciled resources and image identities, and avoid attributing an unverified version to the serving runtime.

## Completion checkpoint

Record the live component conditions, effective serving configuration, API availability, image identities, dashboard/gateway checks, and final cluster health. Stop before project preparation. Model deployment, storage provisioning, and actual project-admin authorization remain later-stage tests.

## Cleanup and rollback

No model or user data is created in this stage. To undo only the dashboard feature overrides, restore the previously recorded values in the dashboard settings overlay and apply it; do not delete the shared ODH dashboard configuration object. To disable a newly enabled component, change its managementState to `Removed` in the repository and apply the same overlay as cluster-admin, then verify reconciliation. This can remove serving infrastructure, so inspect workloads before doing it in an environment with models. Do not delete the pre-existing DSCI, gateway, authentication configuration, or cert-manager as cleanup for this module. Do not remove the DataScienceCluster to troubleshoot an individual pod without reviewing its managed resources.

## Official sources

- [OpenShift AI 3.5 component installation](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html/installing_and_uninstalling_openshift_ai_self-managed/installing-and-deploying-openshift-ai_install)
- [Model-serving platform and runtime configuration](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html/configuring_your_model-serving_platform/configuring-model-servers_rhoai-admin)
- [ServingRuntime and InferenceService concepts](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html/configuring_your_model-serving_platform/configuring-your-model-serving-platform_rhoai-admin)
- OpenShift AI 3.5 release notes, including 3.5.1 (private local evidence; excluded from the public repository)
