# GitOps handoff

Follow [OAI-06](../docs/06-gitops.md). `application.yaml` is an explicit-placeholder template for an existing Argo CD installation; it is not ready to apply unchanged. No GitOps installation, repository push, Application creation, sync, or deletion was performed by the walkthrough review.

Keep the application pointed at `deploy/overlays/lab` relative to the repository root (or its actual enclosing directory). The model weights must already exist on the claim. Platform operators, project creation, role assignment, and download Jobs are separate prerequisites; do not include them by pointing Argo CD at the entire repository.
