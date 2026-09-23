# OAI-04A — Access the model through an HTTPS Route

Applicability: reference OpenShift 4.22.13, OpenShift AI 3.5.1, standard KServe deployment. This supplement supersedes the earlier internal-only lab decision. It does not complete the answer-quality gate or implement the browser chatbot.

## Objective, role, and prerequisites

Expose the model API under the cluster's application domain. A Route connects external HTTPS clients to a project Service. Re-encryption protects both the client-to-router and router-to-proxy connections. The model's existing authentication proxy validates an OpenShift bearer token and checks whether its owner can `get` the `command-helper` InferenceService in this project.

Required role: project-scoped built-in `admin`, tested as `ai-user`. Prerequisites: the running Stage 4 model, installed OpenShift AI controllers, working cluster ingress/DNS/certificates, and an authenticated local `oc` session. Python 3 and curl are required for the test helper.

Administrator prerequisite: the installed platform controller must be permitted to manage authentication delegation for the model service account. The controller handles this when endpoint authentication is enabled. Do not grant cluster-wide privileges to the project user. The model container still masks its Kubernetes API-token path; the platform proxy retains a projected token for authentication and authorization checks.

## Apply and inspect

Run from the repository root:

```bash
oc whoami
oc whoami --show-server
oc apply --dry-run=server -k deploy/overlays/lab-model
oc apply -k deploy/overlays/lab-model
oc rollout status deployment/command-helper-predictor -n intro-openshift-ai --timeout=60s
oc get route command-helper -n intro-openshift-ai -o yaml
```

Expected identity/API: `ai-user`, `https://api.lab.example.com:6443`. Model reload can take longer than one minute; inspect pod progress and repeat the bounded readiness check.

`deploy/overlays/lab-model/model-route-access.yaml` is the complete Kustomize patch controlling exposure and authentication. It sets `networking.kserve.io/visibility: exposed` and `security.opendatahub.io/enable-auth: "true"`. OpenShift AI generates and owns the Route. Do not add a second, competing Route manifest or manually edit the generated Route. Kustomize owns the desired inputs; the controller owns the derived resource.

The policy retains labeled internal clients on TCP 8080 and permits router traffic from the OpenShift ingress namespace group only on TCP 8443. The selector is `policy-group.network.openshift.io/ingress: ""`, which OpenShift supports for OVN-Kubernetes router traffic. Selecting only the namespace name failed in this lab with host-networked routers; the documented ingress selector passed. No namespace labels are changed. No MIG, sharing, node label, or additional replica is introduced. The lab Service changes to HTTPS port 8443. Direct internal headless-DNS access on port 8080 remains restricted by the existing client-label policy.

Expected Route: `Admitted=True`, TLS `reencrypt`, HTTP-to-HTTPS redirect, target Service `command-helper-predictor`, target port `https`. The generated Route relies on the router's service CA trust; no private certificate material is committed.

Console inspection alternative: select project `intro-openshift-ai`, inspect its Route resource `command-helper` and the YAML fields above. Use the console resource search if navigation differs by perspective. Do not create another Route in the console. Opening its URL does not provide a chat page or an interactive OpenShift login form: this proxy expects a bearer token.

## Test from your workstation

API base:

`https://command-helper-intro-openshift-ai.apps.lab.example.com/v1`

```bash
python3 checks/model-route.py
python3 checks/model-route.py --prompt 'Explain the difference between a Kubernetes Pod and a Deployment.'
```

The helper verifies the intended cluster and reviewed hostname before sending credentials. It reads the current login token into memory and passes it to curl through standard input, not command arguments, logs, or a file. TLS certificate validation stays enabled; redirects are not followed. Do not enable shell tracing or verbose HTTP tracing when adapting authenticated tests.

Expected: anonymous `/v1/models` returns 401 or 403; authenticated model listing and `/v1/chat/completions` return 200. The helper sends the repository's draft system prompt. A transport pass does not establish answer correctness. Generated commands are printed and never executed.

## Troubleshoot

- 401: login is missing or expired. Reauthenticate through your normal local `oc` workflow. Browser console cookies are not bearer tokens for this API.
- 403: verify `oc auth can-i get inferenceservices.serving.kserve.io/command-helper -n intro-openshift-ai`. If permissions pass, an administrator must inspect the controller-managed authentication-delegation binding and proxy errors.
- 503: confirm the documented ingress namespace-group selector is present; a namespace-name selector did not work for this lab’s host-networked routers. Inspect model pod readiness, Route admission, Service endpoints, service-certificate readiness, and router network access on 8443. Authentication changes can replace the model pod; wait for its weights to reload.
- Certificate/DNS failure: verify the cluster application wildcard and workstation trust. Do not disable certificate verification.
- 504: the generated Route has a 30-second timeout. Keep the initial requests short; review controller-supported timeout settings before larger workloads.

## Checkpoint and rollback

Record the admitted Route, anonymous rejection, authenticated model listing/completion, Ready replica count, and model-token absence check. Keep output evidence free of credentials. OAI-04 still requires its separate answer-quality acceptance; record that gate separately from the working Stage 5 reference-assisted UI.

To remove external access while retaining the internal model, change this patch's visibility value to `cluster-local`, remove its router-specific ingress rule, and reapply the lab overlay. Leave endpoint authentication enabled until Route removal is confirmed. Confirm `oc get route command-helper -n intro-openshift-ai` returns NotFound. Do not merely delete the Route: the controller would recreate it while `visibility: exposed` remains. Retain the model PVC.

## Sources

- [OpenShift 4.22 Routes and TLS](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/ingress_and_load_balancing/routes).
- [Open Data Hub Route controller](https://github.com/opendatahub-io/odh-model-controller/blob/main/internal/controller/serving/reconcilers/kserve_raw_route_reconciler.go). Upstream main explains behavior; it is not asserted to be the exact installed build. Verify generated resources against the installed cluster.
- Installed API schema: `oc explain route.spec.tls.destinationCACertificate`; observed proxy authorization ConfigMap: `command-helper-kube-rbac-proxy-sar-config`.

- [OpenShift 4.22 network policy and ingress selector](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/network_security/network-policy).
