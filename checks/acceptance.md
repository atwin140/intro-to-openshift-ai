# Intro to OpenShift AI — acceptance checklist

Historical reference results only; the original deployment has since been reset. For a new cluster, copy this checklist into private notes and reset all checks to unchecked.

Applicability: reference whole-GPU lab. Updated 2026-09-23. Checked items represent bounded observations, not a fresh installation replay or vendor support certification. Earlier chronological observations remain in local progress/evidence files. See [walkthrough review](walkthrough-review.md).

## Platform and handoff

- [x] OAI-00: versions, node/GPU inventory, virtualization evidence, storage configuration, and support boundaries recorded.
- [ ] Current cluster health: authentication operator Degraded due to Keycloak connection timeout; fresh-login readiness unresolved. All nodes Ready and machine configuration pools healthy at review.
- [x] OAI-01: both workers passed pinned CUDA computation tests; driver and whole-GPU resources verified; no sharing enabled. Historical computation results are not re-run while both GPUs serve models.
- [x] OAI-02: dashboard/KServe configuration and served APIs verified; operators installed. Platform authentication health is tracked separately above.
- [x] OAI-03: initial PVC write/read relocation passed on both workers; actual ai-user permissions and ConfigMap create/read/delete handoff previously passed; dashboard project access previously observed. Current effective permissions rechecked including exec and port-forward. This does not prove a new identity-provider login today.

## Model and chat

- [x] OAI-04 serving: one command-helper replica on one GPU, pinned model/runtime, inference readiness and bounded one/two-request memory checks passed.
- [ ] OAI-04 model-answer quality: unresolved; model-generated answers can contain incorrect or incomplete commands/explanations. See [quality review](model-quality-review.md).
- [x] OAI-04A: Route admitted; anonymous model listing 401; authenticated listing/completion 200. Current review used the active administrator login; project-user access was separately tested during initial setup.
- [x] OAI-05 browser behavior: anonymous UI, command-copy controls, New chat, and generated responses previously observed. Current API/input/origin/concurrency regression passed.
- [x] OAI-05 eviction example: exact supported question returns a labeled static reviewed reference with correct reason/phase distinction, scope, jq, oc, and kubectl examples. This is not a model-only quality pass.
- [x] OAI-05 security: no chatbot API token, no added application RoleBinding, no command-execution feature; restricted network path. Model's platform proxy retains its documented token; model-container credential path is masked.
- [x] OAI-05 bounded concurrency/context: two requests each with 12,583 input tokens passed; sampled peak 11,045 MiB used, 831 MiB free; automatic history trimming passed. Distinct-marker smoke test found no cross-marker response. This does not establish sustained load capacity or comprehensive privacy isolation.
- [x] Tone guide included by the server on every model request; one customer-update example checked. Compliance is not guaranteed.

## Documentation and optional work

- [x] Model-only Stage 4 and combined Stage 5 overlays render; combined output unchanged after restructuring. Server dry runs pass as ai-user.
- [x] OAI-06 repository instructions and explicit-placeholder Application example prepared; bootstrap roles and storage/deletion risks documented.
- [ ] Actual Argo CD registration, manual sync, health integration, rollback, and retention behavior tested in the target installation.
- [x] OAI-07 optional retrieval/H100/sharing plans separated from validated instructions.
- [ ] Retrieval, time-slicing, and H100 MIG implemented and validated. None is required for the base demo.
- [ ] Independent clean-install replay and destructive cleanup/restore exercise. Deliberately not performed on the running lab.

## Evidence

Local evidence is excluded from Git. Main records: stage1 CUDA/operator snapshots; stage3 actual-user handoff; stage4 model/Route/network tests; stage5 browser/API/concurrency tests; context-expansion.json; tone-guide-check.json. Current review adds walkthrough-structure.txt, walkthrough-role-check.txt, walkthrough-chat-check.txt, walkthrough-route-check.txt, and the review report.

The separate image generator now performs inference on gpu-worker-02. Its own [validation](../image-generation/VALIDATION.md) does not prove the chat model was relocated or tested there. Both GPU workers were tested for the original CUDA/storage handoff; the initial chatbot still uses gpu-worker-01 only.

## Reset and reuse

- [x] Guarded reset script provided; project preview inspected on reference and mocked safety tests passed.
- [ ] Destructive project removal, storage cleanup and redeployment tested on a disposable lab.
- [ ] AI/GPU teardown and subsequent reinstall tested on a disposable lab.
- [ ] Separate one-GPU cluster overlays prepared and validated for each new cluster.

See [reset module](../docs/08-reset-and-reuse.md). No live reset has been performed.
