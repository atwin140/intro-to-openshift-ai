# Public release review

Reviewed 2026-09-23. This repository is a configurable training lab, not a guaranteed turnkey installer. The original cluster demonstrated GPU compute, storage, model serving, browser chat and bounded two-request operation. Its project and GPU operator namespaces were absent at this review after the user's reset. No fresh inference or complete teardown/reinstall claim is made here.

## Corrections for sharing

- Replaced private endpoints, administrator identifiers and worker names in shareable sources with examples. Raw evidence and original source snapshots remain local and ignored.
- Removed public Markdown dependencies on excluded private notes/inventory. Expanded link validation to all Git-candidate Markdown files.
- Excluded workstation metadata, Python caches and generated artifacts.
- Made evidence-producing checks create missing output directories on a fresh checkout.
- Added new-cluster preparation covering every required overlay edit, registry access, namespace security allocation and role boundaries.
- Added a single-GPU validation overlay that removes the second simultaneous GPU test Job. A one-worker storage test demonstrates same-worker remount, not cross-worker relocation.
- Corrected README status so historical demonstrations are not presented as a currently hosted service.
- Added local HTTP-handler tests using a stub model and a credential-pattern publication scan. Neither is a model-quality or GPU test.

## Validation and limits

Run these from the repository root:

```bash
python3 checks/publication-check.py
python3 checks/review-walkthrough.py
python3 checks/test-reset-lab.py
python3 checks/test-chatbot-local.py
```

The release preparation also checks an isolated Git-index export without ignored local files. Structural checks cover 38 Kustomize roots, Python/shell syntax and Markdown links. Reset safeguards have 18 tests; local chat has six tests for health, reviewed reference, malformed input, role/origin rejection and system-prompt forwarding. Live execution is required to establish image availability, operator compatibility, storage, serving admission and actual GPU memory behavior on each new cluster.

Outstanding: fresh-cluster replay, one-GPU end-to-end acceptance, general generated-command quality, Argo CD sync and independent participant feedback. Do not turn historical checked boxes into acceptance for a new cluster. Retained GPU CRDs/host state after reset are not a clean OS baseline. Read the reset module before reuse.

## Publishing

The repository contains author-created scripts and instructions plus links to externally licensed models and vendor images. No weights or container images are included. A project license has not been selected; public visibility alone does not grant an open-source license. Select a license consistent with the owner's rights before advertising unrestricted reuse. Model and image terms remain separate.

Review `git diff --cached --stat`, run the checks above, then commit and push to the intended public repository. Do not add ignored evidence or credentials with `git add -f`. Personalized cluster settings should stay in a private working copy or private configuration branch. The public template must retain its example endpoints.
