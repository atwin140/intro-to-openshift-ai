# Intro to OpenShift AI

A staged lab for preparing GPU workers, serving a small model through OpenShift AI, and deploying a browser chat interface. Start with the applicable stage and stop at its checkpoint. All commands assume the repository root unless stated otherwise.

## Start here

This is a public, configurable lab template. Follow [new-cluster setup](docs/00-new-cluster.md) before applying any overlay. Example domains, worker names, storage settings and filesystem group values must be replaced with your discovered values. The default layout has two GPU workers; the setup module explains the one-GPU path.

The original lab demonstrated model serving, browser chat and two concurrent requests on an RTX 4070. It has since been reset. Historical checks are not evidence that a fresh clone has been deployed successfully. General model-answer quality remains unaccepted; the exact eviction example uses a labeled reviewed reference. RTX 4070 operation is locally validated, not vendor hardware certification.

Publication review: [release review](checks/release-review.md). Raw inventory, private progress notes and credentials are excluded. Do not treat example URLs as a hosted demo.

## Stages and role boundaries

| ID | Module | Required role | Checkpoint |
| --- | --- | --- | --- |
| OAI-00 | [Discover](docs/00-discovery.md) | Cluster-admin | Versions, health, hardware, and storage inventory |
| OAI-01 | [Enable GPUs](docs/01-gpu-enablement.md) | Cluster-admin | Driver and CUDA test on both workers |
| OAI-02 | [Prepare OpenShift AI](docs/02-openshift-ai.md) | Cluster-admin | Dashboard and serving components Ready |
| OAI-03 | [Hand off the project](docs/03-project-handoff.md) | Cluster-admin, then project admin | Storage test and actual-user permissions |
| OAI-04 | [Serve the model](docs/04-model-serving.md) | Project admin | Inference, memory, and separate answer-quality checks |
| OAI-04A | [HTTPS API access](docs/04a-model-route.md) | Project admin | Authenticated API works; anonymous access rejected |
| OAI-05 | [Browser chatbot](docs/05-chatbot.md) | Project admin | Anonymous UI, reviewed reference, two-user tests |
| OAI-06 | [GitOps handoff](docs/06-gitops.md) | Project admin for source; Argo CD admin for bootstrap | Prepared files; actual GitOps adoption untested |
| OAI-07A | [Guide retrieval](docs/extensions/guide-retrieval.md) | Depends on selected components | Optional design, not deployed |
| OAI-07B | [Second deployment, sharing, H100](docs/extensions/h100-and-gpu-sharing.md) | Cluster-admin and project admin | Separate hardware-specific validation |

The built-in OpenShift `admin` role is scoped to `intro-openshift-ai` for `ai-user`. Cluster-admin resources live under `platform/` and are never part of the application overlay. Use a verified actual project-user context, not administrator impersonation, for handoff acceptance. Console instructions lead for infrastructure; CLI/Kustomize instructions lead for application deployment. Console inspection is an alternative view, not a second deployment method.

## Tested reference configuration

- Observed OpenShift 4.22.13, OpenShift AI operator 3.5.1, GPU Operator 26.7.0, driver 595.91.07. Reverify before reusing this guide on another environment.
- Each GPU worker exposes one RTX 4070 with 12,282 MiB. No MIG or time-slicing. [Compatibility and support boundaries](docs/00-gpu-compatibility.md).
- Command helper: pinned Qwen2.5-Coder-7B-Instruct-AWQ on pinned Red Hat vLLM, one replica and one whole GPU on gpu-worker-01.
- Context: 16,384 tokens total, up to 2,048 output tokens, two active model requests. Two long requests retained 831 MiB minimum sampled free GPU memory; short tests do not establish every possible peak.
- Chat: up to 16,000 characters per message and twenty prior exchanges, with token-aware removal of oldest exchanges. History is browser-memory-only. The tone guide in `chatbot/prompts/assistant.md` is included on every model request.
- The application cannot execute commands and has no Kubernetes API token. It uses the restricted private model path without credentials; the public model API requires an OpenShift bearer token. Any future endpoint credentials must remain server-side and out of Git/browser code.
- The separate [image-generation lab](image-generation/README.md) used the second worker in the reference deployment; see its own [validation](image-generation/VALIDATION.md). On a one-GPU cluster, omit this extension while the chatbot model is running.

## Deployment order

For an existing, correctly prepared project, the application sequence is:

1. Verify identity and API endpoint, then Stage 3 permissions.
2. Apply `deploy/storage/overlays/lab` and verify the model claim.
3. Apply `deploy/download/overlays/lab`, wait for the pinned weights, record logs, and remove the completed downloader.
4. Apply `deploy/overlays/lab-model` for Stage 4 model-only deployment and HTTPS API.
5. After the checkpoint, apply `deploy/overlays/lab` for the combined model and chat.

Use the complete commands, dry runs, checks, and failure handling in each module. Do not replay operator installation or download steps merely to inspect an already running system. Lab-specific node names, fsGroup, storage class, namespace, API address, and Route hostnames require review when copying to another cluster.

The model-only and combined overlays render the same shared model resources. Applying Stage 4 after Stage 5 does not remove the chatbot because apply does not prune. One GitOps Application should own the combined overlay; avoid overlapping owners.

## Verification

Structural checks require Git, `oc`, Python 3, and Bash, but do not modify the cluster:

```bash
python3 checks/review-walkthrough.py
```

Application checks send a small number of inference requests:

```bash
python3 checks/project-permissions.py ai-user --context='<your-project-user-context>'
python3 checks/chatbot.py
python3 checks/model-route.py
```

The permissions command uses the named existing login without changing the active context. The authenticated Route helper uses the active `oc` login; check identity and intended endpoint first. It keeps tokens in memory. For a bounded longer context/memory test, use `python3 checks/chat-context.py`; it can load the GPU for tens of seconds. Do not run it alongside an important demo. See [acceptance](checks/acceptance.md) for evidence and unresolved criteria.

The structural review is not a clean-install replay. Destructive cleanup, hardware repartitioning, and initial identity-provider login require separate checkpoints.

## Reset for the next participant

Use [OAI-08 — Reset and reuse](docs/08-reset-and-reuse.md) and [the guarded reset script](scripts/reset-lab.py). Preview is read-only; execution deletes the selected scope. Routine project reset keeps GPU/AI platform preparation. Separate AI/GPU teardown stages are provided but are not yet live validated. A clean driver/operator course is best served by reprovisioning dedicated clusters. Each separate cluster can use one 4070; current two-worker overlays require adaptation.

## Repository and cleanup

Follow [GitOps handoff](docs/06-gitops.md) to copy the working directory into an approved Git repository and fill the [Application template](gitops/application.yaml). No GitOps installation is required for manual deployment. Private `notes/` and `inventory/` hold lab evidence and are ignored; they are not required by the reusable instructions. Keep secrets out of all committed files.

To stop the UI, follow the targeted commands in Stage 5. To stop the model but retain data, follow Stage 4. Never use `oc delete -k deploy/overlays/lab` as a routine stop command: it includes the model claim, whose storage class has Delete reclaim policy. Full data deletion, platform removal, and Argo CD cascading deletion require separate review. Cleanup instructions were reviewed but not executed against the working demo.

Guide Markdown can later become retrieval reference material. Storing files alone does not teach the model their contents; a retrieval integration must select approved excerpts and supply them with each question.
