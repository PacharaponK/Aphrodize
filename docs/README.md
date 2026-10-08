# Aphrodize documentation

Start with the [root quick start](../README.md). This index describes repository capabilities; it does not certify that a deployment has credentials, model files, or fresh data. README entry points are in English; some detailed reports retain their original Thai text.

## Find a workflow

| Task | Guide |
| --- | --- |
| Understand features and limitations | [Product and scope](project/Product%20and%20Scope.md) |
| Review consent, privacy, and claims | [Safety and governance](project/Safety%20and%20Governance.md) |
| Inspect runtime architecture | [Runtime diagram](architecture/diagrams/diagram.md), [component flows](architecture/Component-Flows.md) |
| Inspect database and accounts | [Database ER](architecture/diagrams/database-er.md), [authentication design](architecture/Auth-Account-Database-Design.md) |
| Run image inference and understand AI | [AI README](../ai/README.md), [AI and data](ai/AI%20and%20Data.md) |
| Configure annotation and image training | [Annotation review](ai/Annotation-Review.md), [curated training](ai/Curated-Training.md), [human review](ai/Human-Review.md) |
| Enter Daily Health records | [Input flow](lifestyle/Daily-Health-Input-Flow.md) |
| Distinguish calculations, baseline models, and forecasts | [Lifestyle model summary](lifestyle/Lifestyle-Model-Summary.md), [model contract](../models/time-series/non-linear-model/README.md) |
| Import, train, promote, or delete health data | [Daily Health training pipeline](lifestyle/Daily-Health-Training-Pipeline.md) |
| Understand removed acne scope and cleanup APIs | [Acne observation protocol](lifestyle/Acne-Observation-Protocol.md) |
| Operate city UV forecasts and product rules | [UV operations](uv-implementation.md), [model workflow](uv-model-workflow.md) |
| Use the 77-area Thailand UV map | [Map guide](uv-thailand-map.md) |
| Review UV candidates, gates, and rollback | [UV MLOps](uv-mlops-report.md) |
| Deploy the web VM and GPU workers | [VM deployment](deploy-vm.md), [GPU deployment](deploy-gpu.md) |
| Configure CI, branch protection, and releases | [Main protection](ci-main-protection.md), [VM CI/CD](cicd-vm.md) |
| Configure tool links | [Services portal](services-portal.md) |
| Configure metrics, logs, dashboards, and Discord alerts | [Observability](observability.md) |
| Find outstanding work | [Roadmap](roadmap.md) |

## Evidence and specialist references

- Image/MLOps flows: [photo data](architecture/diagrams/ai-photo-data-flow.md), [review pipeline](architecture/diagrams/ai-review-mlops-flow.md), [input/training/output](architecture/diagrams/full-input-retraining-output-flow.md).
- Landmarks and wrinkle regions: [ROI guide](architecture/face-landmark-rois.md), [area implementation](ai/implementation/Wrinkle-Area-Implementation.md).
- Research evidence: [FFHQ implementation summary](ai/implementation/FFHQ-Wrinkle-Implementation-Summary.md), [EDA](ai/EDA.md), [UV data feasibility](uv-data-feasibility.md).
- Product provenance: [catalog review dated 2026-10-01](research/thai-product-catalog-2026-10-01.md), [additional wrinkle-care review dated 2026-10-07](research/wrinkle-product-catalog-2026-10-07.md). Labels and prices reflect the recorded review, not live retailer data.

Dated test reports describe their recorded run, not current verification. Older `.dio`/PNG diagrams are design references; check Mermaid diagrams and ORM definitions for current behavior. Superseded documents remain available through `git log -- docs/` and `git show <commit>:docs/<path>`.

When changing behavior, update its primary guide and code references. Verify endpoints against OpenAPI and data structures against [database models](../backend/core/db/models.py). Link to existing guides instead of duplicating setup instructions.
