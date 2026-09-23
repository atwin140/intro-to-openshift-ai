# Deployment validation — September 22, 2026 (America/Chicago)

The image-generator InferenceService is Ready in `intro-openshift-ai` on the reference cluster. Its predictor has two Ready containers, zero restarts, and one whole GPU assigned on `gpu-worker-02`. The existing command-helper and chatbot remain Ready on their original nodes.

## Observed results

| Check | Result |
| --- | --- |
| Pinned model download | Complete; four FP16 safetensors components, 2,740,623,950 bytes |
| Anonymous HTTPS access | Rejected, HTTP 401 |
| Invalid bearer token | Rejected, HTTP 401 |
| Current reference user access | HTTP 200 |
| Empty/blank description, invalid step count/type, unknown fields, excess tokenizer length | HTTP 422 |
| JSON body over 8 KiB | HTTP 413 |
| Lighthouse image, 25 steps | 512 × 512 PNG; 1.68 seconds server generation time |
| Fox image, 40 steps | 512 × 512 PNG; 2.09 seconds server generation time |
| Two simultaneous image requests | One HTTP 200, one HTTP 429; retry hint returned |
| Peak PyTorch GPU allocation during both sample requests | 3,258 MiB |
| Total GPU memory observed after tests | 4,037 MiB of 12,282 MiB |
| Saved command-line client | Generated a third 512 × 512 PNG; 1.39 seconds server generation time |
| Direct HTTP model port from the unlabeled chatbot pod | DNS resolved; connection timed out as required by ingress policy |
| Model process Kubernetes credentials | Empty read-only mount masks the API credential directory |

Generation timings exclude client transport and PNG download. PyTorch allocation does not include every driver/runtime allocation. The total-memory observation is a point-in-time reading after generation, not a continuously sampled total peak.

Both PNGs were visually inspected. The fox is recognizable and matches the prompt. The lighthouse scene has the requested watercolor/coastal appearance, but the lighthouse is cropped at the upper-right edge. These samples establish functional image generation, not broad image-quality acceptance. The model's safety checker is loaded and retained; no comprehensive moderation benchmark was performed.

Evidence: `../inventory/image-generator-verification.json`, `image-generator-service.json`, `image-generator-pod.json`, `image-generator-deployment.json`, `image-generator-route.json`, `image-generator-runtime.log`, and `image-model-download.txt`. Samples are in `../../outputs/image-generation/`.

## Operating scope

This is an authenticated lab API with a command-line PNG client. It has no browser editor or training workflow. The custom Diffusers runtime and RTX 4070 configuration are locally validated, not asserted to be a vendor-supported production combination. One request runs at a time. The model remains running and reserves the second GPU until the image deployment is removed.
