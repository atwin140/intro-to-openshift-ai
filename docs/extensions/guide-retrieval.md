# OAI-07A — Retrieve approved guide content (optional)

Applicability: design only; no retrieval service or index is deployed. Required roles: project administrator for an approved project-scoped implementation; cluster-admin for any new platform prerequisite. Prerequisites: working Stage 5, approved source documents, selected compatible embedding model and storage, and a separate memory budget.

## Objective and explanation

Retrieval searches approved documents and adds relevant excerpts to a model request. Saving Markdown or adding a tone prompt does not teach the model the guide. Keep stable module identifiers, applicability, and official source links. Keep lab-progress notes and credentials out of the index unless separately reviewed for inclusion.

## Planned procedure and checks

1. Inventory approved modules and version them with the code.
2. Select and verify an embedding runtime and vector/search store; do not assume the 4070 has spare capacity for another GPU model.
3. Index sections with module ID, revision, title, and source URL. Retrieve a small number within the 16K context budget.
4. Render citations and explicitly label missing/outdated evidence. Treat retrieved content as data, never instructions to execute tools.
5. Test answerable, unanswerable, conflicting-version, and prompt-injection examples. Verify citations actually support the answers and no credentials enter the index.

CLI/Kustomize manifests and console inspection instructions will be added only after component selection; no guessed resource fields or install commands are executable in this design module. A second user must not retrieve another user's private data.

## Failures, checkpoint, and cleanup

Wrong answers despite retrieved text require reviewing retrieval relevance and model behavior separately. More excerpts can consume context without improving accuracy. Completion requires measured retrieval quality, supported deployment files, and negative access tests; it is currently unvalidated. Rollback should disable retrieval in the server, preserve the base chat, then remove only the approved index/resources after retention review.

Source: [OpenShift AI model deployment](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html/deploying_models/deploying_models). No specific retrieval component is selected by that link.
