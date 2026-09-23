# OAI-05 — Simple browser chat

Applicability: reference OpenShift 4.22.13 / OpenShift AI 3.5.1, with the Stage 4 command-helper model running. Required role: project-scoped built-in admin in intro-openshift-ai, tested using ai-user. No additional cluster-admin preparation is needed for this stage.

## Objective and behavior

Provide an anonymous HTTPS web chat for one or two lab users. The page includes conversation history, New chat, example questions, and code-copy buttons. It only displays text; it has no command execution feature or Kubernetes client. The server sends requests to the model's private, network-restricted port 8080. It does not use or expose your personal OpenShift token. The separate public model API remains authenticated.

Up to twenty completed exchanges accompany each new question. The server measures actual tokens and removes oldest exchanges when needed to reserve room for the answer. A status notice reports removed exchanges. History is held only in the page's memory and disappears on reload or New chat. The server stores no conversation history and does not log request bodies. Browser users see only their own local history. The anonymous URL is accessible to anyone who can reach the cluster ingress; this is a lab interface, not a production public service.

The server permits two simultaneous model requests, limits request bodies to 400,000 bytes and conversation content to 96,000 characters, and caps generated output at 2048 tokens. The text box permits 16,000 characters per message. Before generation, the server calls the installed runtime's /tokenize API, including the system prompt and chat template. It retains at most 14,336 input tokens, reserving 2048 within the 16,384-token context. Older exchanges are removed first; a single oversized message is rejected. The status line reports actual input/output tokens, response time, trimming, and output-limit completion. Server generation timeout is 120 seconds, browser timeout 135 seconds, and Route timeout 150 seconds. Larger context permits more history but does not guarantee better reasoning or sustained GPU load.

The exact question “How do I list all evicted pods?” and two simple variants return a labeled, reviewed command reference. This intentionally avoids the previously observed model error. Other questions use the model and are labeled accordingly. The reference is static application content, not model learning or retrieval. Broader answer-quality acceptance is still unresolved.

## Files and deployment

Stage 4 uses `deploy/overlays/lab-model` (model and storage only). Stage 5 uses `deploy/overlays/lab`, which includes that model overlay and the chatbot. Reapplying Stage 4 does not delete an existing chatbot; apply does not prune resources.

- chatbot/src/: Python server, HTML, CSS, and JavaScript; no third-party packages or browser CDNs.
- chatbot/prompts/assistant.md: system instructions supplied by the server.
- chatbot/kustomization.yaml: content-hashed ConfigMap generated from source files.
- deploy/chatbot/base/: complete project-scoped Deployment, Service, ServiceAccount, Route, and NetworkPolicy.
- deploy/overlays/lab/chatbot-settings.yaml: reference hostname and allowed browser origin.
- chatbot/Containerfile: optional image packaging. The deployed lab mounts the source ConfigMap into a pinned Red Hat Python image, so no image build is required. The image digest was resolved from the installed python:3.12-ubi9 ImageStreamTag.

From the repository root:

```bash
oc whoami
oc whoami --show-server
oc apply --dry-run=server -k deploy/overlays/lab
oc apply -k deploy/overlays/lab
oc rollout status deployment/chatbot -n intro-openshift-ai --timeout=60s
oc get route chat -n intro-openshift-ai
python3 checks/chatbot.py
```

Verify ai-user and https://api.lab.example.com:6443 before applying. Reapply after source edits; ConfigMap hash changes trigger a Deployment rollout. Retain the model/storage resources. The generated source ConfigMap contains no credentials.

Open https://chat-intro-openshift-ai.apps.lab.example.com. No login or token entry is required. Enter a question, select Send, and wait for an answer. Enter sends; Shift+Enter inserts a newline. Use Copy for a code block and review it before using it yourself. New chat clears the page's conversation.

Console inspection alternative: select project intro-openshift-ai and inspect Deployment chatbot and Route chat. Expect an available replica, Route admission, edge TLS, and an HTTP-to-HTTPS redirect. Deployment changes are made through Kustomize; console inspection does not replace the source files.

## Security and checks

The chatbot service account has automountServiceAccountToken=false and no added RoleBinding. The application runs non-root under restricted-v2, drops capabilities, and has a read-only filesystem. The NetworkPolicy permits ingress from the OpenShift ingress namespace group on 8080 and egress only to the model on 8080 and cluster DNS on 5353. The browser calls only the chat server. The server's model URL is fixed by deployment configuration; user input cannot select another destination. Answers are rendered as text nodes, with limited code/bold formatting, rather than injected HTML.

Checks cover anonymous HTTPS access, reviewed eviction content, rejection of client system messages and foreign browser origins, oversized conversation rejection, and two simultaneous model requests with distinct markers. The origin check is a browser safeguard, not authentication or protection against arbitrary HTTP clients. Rate limits, production server hardening, and persistent conversation storage are not implemented. Python's standard HTTP server is used specifically for this small lab, not as a production hosting recommendation.

Manual checkpoint: submit a general question, inspect the answer label, submit the eviction example, copy a code block, then select New chat. Confirm no credentials are requested. Verify the running pod has no mounted service-account token. A separate diagnostic socket test confirmed the Kubernetes API connection is blocked; the application code itself contains no Kubernetes access path.

## Troubleshooting

- Route 503: inspect Deployment readiness and image-pull events. Initial image pull can exceed a one-minute wait.
- Chat says model unavailable: check command-helper readiness and both NetworkPolicies. The model Service is headless; use its pod port 8080 for this private path.
- 403: compare PUBLIC_ORIGIN in the lab patch with the actual browser URL.
- 429: two model calls are already active; retry shortly.
- Context rejection: start a new chat or shorten the message. Do not increase the model context without repeating GPU-memory tests.
- Incorrect answer: inspect whether it is model-generated. The reviewed eviction response does not validate unrelated model answers. Do not run generated commands automatically.

## Cleanup and rollback

To stop only the chatbot, remove `../../chatbot/base` and the `chatbot-settings.yaml` patch entry from `deploy/overlays/lab/kustomization.yaml`, then explicitly remove its resources:

```bash
oc delete route/chat service/chatbot deployment/chatbot serviceaccount/chatbot networkpolicy/chatbot-network -n intro-openshift-ai
```

Kustomize apply does not prune removed resources. Inspect ConfigMaps and delete only obsolete chatbot-code-* entries after no pod references them. Do not use oc delete -k on the combined lab overlay: it includes the model PVC. To roll back application edits, restore the previous chatbot source/configuration and reapply the lab overlay. The Containerfile is optional packaging and is not used by this ConfigMap deployment.

## Sources

- [OpenShift 4.22 Routes](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/ingress_and_load_balancing/routes).
- [OpenShift 4.22 NetworkPolicy](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/network_security/network-policy).
- [Python 3.12 HTTP server limitations](https://docs.python.org/3.12/library/http.server.html).
- [Kubernetes node-pressure eviction](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/) and [supported field selectors](https://kubernetes.io/docs/concepts/overview/working-with-objects/field-selectors/).

Context expansion verification: `python3 checks/chat-context.py` tests concurrent requests exceeding the old context and automatic removal of oversized old exchanges. [vLLM tuning and cache trade-offs](https://docs.vllm.ai/en/latest/configuration/optimization/).

## Persistent tone instructions

The AHEAD tone guide is stored in `chatbot/prompts/assistant.md`. The server includes this file as a system message in every model request and in its context-token calculation. Users do not need to repeat it after New chat. Edit the file and reapply the lab overlay; the content-hashed ConfigMap triggers a chatbot rollout that reloads it. The system message is retained when old conversation exchanges are removed.

This is application-level instruction, not model training or permanent model memory. Calls made directly to the model API do not inherit it unless the caller supplies it. The static reviewed eviction reference bypasses generation and does not change wording automatically. Tone compliance is best effort; review important communications before use.
