# Aphrodize architecture overview

This is the project architecture in text form. The `.dio` file remains the original object diagram; this Markdown file is the editable overview for discussing structure and direction.

## Runtime tree

```text
Aphrodize
├── Web interface
│   ├── consent
│   ├── skin-health questionnaire
│   ├── standardized face-image upload
│   ├── analysis result
│   └── history and trend view
│
├── FastAPI central API
│   ├── consent and access control
│   ├── questionnaire API
│   ├── image upload and validation
│   ├── analysis orchestration
│   ├── rule-based possible-factor explanation
│   ├── recommendation safety checks
│   ├── history and trend API
│   ├── deletion API
│   └── health check / OpenAPI
│
├── Image-analysis pipeline
│   ├── image-quality gate
│   │   ├── one face
│   │   ├── frontal pose
│   │   ├── neutral expression
│   │   ├── acceptable exposure and resolution
│   │   ├── low blur
│   │   └── no beauty filter
│   ├── face detection and landmarks
│   ├── face alignment and crop
│   ├── region mapping
│   ├── wrinkle segmentation
│   ├── regional wrinkle score
│   └── confidence and model-version metadata
│
├── Rule and safety layer
│   ├── possible factors from questionnaire answers only
│   ├── rule ID and rule version
│   ├── product category / active ingredient recommendation
│   ├── source and rationale
│   ├── allergy and irritation check
│   ├── contraindication check
│   └── low-quality / low-confidence blocking
│
├── PostgreSQL
│   ├── pseudonymous users
│   ├── consents
│   ├── questionnaires
│   ├── image metadata
│   ├── analyses and model versions
│   ├── regional wrinkle results
│   ├── possible-factor results
│   ├── recommendations
│   └── longitudinal observations
│
├── MinIO object storage
│   ├── original image
│   ├── normalized image
│   ├── wrinkle mask
│   └── model artifact
│
└── Operations
    ├── OpenTelemetry
    ├── Grafana dashboards and alerts
    ├── Loki logs
    ├── Tempo traces
    ├── administrator health checks
    └── deletion / retention controls
```

## Runtime direction

```text
Web interface
  → FastAPI
  → image-quality gate
  → face alignment and region mapping
  → wrinkle segmentation
  → regional scores and confidence
  → rule engine and safety checks
  → result API
  → user result and history/trend
```

Storage direction:

```text
FastAPI
  → PostgreSQL       consent, questionnaire, metadata, results, observations
  → MinIO            original/normalized images, masks, model artifacts
```

If GPU inference becomes slow, use the optional asynchronous path:

```text
FastAPI
  → Redis queue
  → analysis worker
  → GPU inference
  → PostgreSQL + MinIO
  → result API
```

For the MVP, keep the worker inside the modular-monolith deployment until GPU latency or concurrency requires a separate process.

## Offline model direction

```text
FFHQ-Wrinkle dataset
  → person-level train/validation/test split
  → preprocessing
  → manual mask review when needed
  → segmentation training
  → Dice / IoU / precision / recall
  → subgroup and image-quality evaluation
  → MLflow model + metrics + config
  → approved model version
  → GPU inference deployment
```

User images are for inference and tracking only; they are not added to training automatically.

## Observability direction

```text
FastAPI / worker / storage / database
  → OpenTelemetry
  → metrics and traces
  → Grafana / Tempo
  → safe logs → Loki
```

Do not put face images, face embeddings, raw questionnaire answers, secrets, or unnecessary personal data into logs.

## Safety boundary

The system may report:

- what was detected from the image;
- wrinkle score and confidence;
- possible factors based on the user’s reported answers;
- product categories or active ingredients that pass safety rules;
- qualified longitudinal observations.

The system must not provide age prediction, face recognition, biometric identity embeddings, disease diagnosis, causal confirmation, prescriptions, treatment claims, or product guarantees.

## Open-source / local-first tool choices

| Concern | Suggested tool |
|---|---|
| API | FastAPI, Pydantic |
| Database access | SQLAlchemy, Alembic, PostgreSQL |
| Vision model | PyTorch, U-Net-style segmentation |
| Face landmarks | MediaPipe Face Landmarker |
| Object storage | MinIO |
| Model tracking | MLflow |
| Telemetry | OpenTelemetry, Grafana, Loki, Tempo |
| Packaging | Docker Compose |
| Testing | pytest, HTTPX, Testcontainers |

