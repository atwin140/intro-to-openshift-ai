# reference image generation lab

This service generates a 512 × 512 PNG from an English text description. It deploys pretrained Stable Diffusion 1.5 through OpenShift AI/KServe on `gpu-worker-02`. It does not train a new model. The existing command-helper remains on `gpu-worker-01`.

## Use the service

Log in to the reference cluster with your normal OpenShift account. Your account must have permission to get the `image-generator` InferenceService in `intro-openshift-ai`. From this directory:

```bash
python3 generate.py 'A watercolor painting of a lighthouse on a rocky coast at sunrise' --output lighthouse.png
```

The client reads the current OpenShift token into memory and sends it over HTTPS. It does not write or print credentials. It saves a PNG and a JSON sidecar containing model, seed, generation time, and peak GPU allocation. Use `--seed` to change the variation and `--steps` to select 10–40 steps (default 25). Use short descriptions, approximately 50 words or fewer; requests beyond the model's 77-token context are rejected instead of silently truncated.

Endpoint: `https://image-generator-intro-openshift-ai.apps.lab.example.com/v1/images/generations`

Request: `POST`, `Content-Type: application/json`, `Authorization: Bearer <current OpenShift token>`.

```json
{"prompt":"A watercolor painting of a lighthouse at sunrise", "negative_prompt":"blurry", "steps":25, "seed":42}
```

The response contains `data[0].b64_json`, a base64 PNG. This is a small custom API with an OpenAI-style image response, not a complete implementation of the OpenAI Images API. There is no separate browser image editor. The model is visible in the OpenShift AI project deployments.

Only one generation runs at a time. Simultaneous requests receive HTTP 429 and a retry hint. Invalid input receives HTTP 422. JSON request bodies are limited to 8 KiB. Generated images are returned to the caller and are not stored by the service. The model's safety checker remains enabled; it is not a complete content moderation system.

## Pinned components

- Model mirror: [stable-diffusion-v1-5/stable-diffusion-v1-5](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5), revision `451f4fe16113bff5a5d2269ed5ad43b0592e9a14`.
- License: CreativeML OpenRAIL-M; see the model card and [license](https://github.com/CompVis/stable-diffusion/blob/main/LICENSE). This community mirror is not affiliated with RunwayML.
- Existing lab runtime image: `registry.redhat.io/rhaii/vllm-cuda-rhel9@sha256:c056e61672b6aea489ad5dde0bd2f8497230f5333e87f7cf6c494eba3bfdc808`.
- Observed libraries: PyTorch 2.11.0, Diffusers 0.39.0, Transformers 5.14.1. The image runs a custom Diffusers application, not its vLLM entry point.
- FP16 safetensors, including the safety checker. No remote model Python code and no package installation at startup.
- One replica, one whole RTX 4070 GPU, 10 GiB Synology persistent storage, 8 GiB requested / 16 GiB maximum host memory.

This is a custom lab runtime, not a claim of Red Hat support for this image-generation configuration. Stable Diffusion 1.5 has limited text rendering, complex composition, and anatomical accuracy. Review generated content before use.

## Deployment and verification

Use the existing reference login and confirm `oc whoami --show-server` returns `https://api.lab.example.com:6443`. All resources below are project-scoped. The namespace must already exist; its allocated filesystem group is `1000000000`. Review that value before reusing the manifests elsewhere.

```bash
oc apply --dry-run=server -k storage
oc apply -k storage
oc apply --dry-run=server -k download
oc apply -k download
oc logs -f job/download-image-model -n intro-openshift-ai
oc wait --for=condition=Complete job/download-image-model -n intro-openshift-ai --timeout=60s
```

A longer download can require repeating the bounded wait. Preserve `DOWNLOAD-VERIFIED` evidence, then delete the completed download job to release the volume before serving:

```bash
oc delete -k download
oc apply --dry-run=server -k deploy
oc apply -k deploy
oc wait --for=condition=Ready inferenceservice/image-generator -n intro-openshift-ai --timeout=60s
python3 generate.py 'A watercolor painting of a lighthouse at sunrise' --output lighthouse.png
```

The runtime loads weights offline from the persistent volume. HTTPS authentication uses the existing KServe authentication proxy. Network policy permits the OpenShift router to reach only the proxy port, 8443. The inference process has an empty, read-only mount over the Kubernetes credential directory; the platform authentication proxy retains its controller-injected token. The dedicated application service account has no additional role bindings.

The code ConfigMap has a stable name. After changing `deploy/server.py`, apply the deployment directory and restart `deployment/image-generator-predictor` to load the new code.

Run `python3 verify.py` to check authentication, input limits, two simultaneous requests, and two PNG outputs. Verification evidence is saved under `../inventory/`, and sample images under `../../outputs/image-generation/`.

## Stop and remove

To stop the image service and remove its route, runtime, code, and network policy while retaining downloaded model files:

```bash
oc delete -k deploy
```

To resume, apply `deploy` again. Deleting `storage` additionally deletes the 10 GiB model volume and dedicated service account; do that only when the cached model is no longer needed. These directories contain only image-generation resources.
