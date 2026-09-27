# ER Diagram — ฐานข้อมูลปัจจุบัน

อ้างอิง SQLAlchemy models ใน [`backend/core/db/models.py`](../../backend/core/db/models.py) ไม่ใช่ schema ที่เสนอไว้ในเอกสารออกแบบเดิม

```mermaid
erDiagram
    USERS ||--o| ACCOUNTS : has
    USERS ||--o{ CONSENTS : accepts
    USERS ||--o{ QUESTIONNAIRES : answers
    USERS ||--o{ DAILY_LIFESTYLE_OBSERVATIONS : records
    USERS ||--o{ DAILY_HEALTH_ENTRIES : records
    USERS ||--o{ ANALYSES : requests
    USERS ||--o{ ANNOTATION_TASKS : owns

    USERS {
        uuid id PK
        datetime created_at
    }

    ACCOUNTS {
        uuid id PK
        uuid user_id FK, UK
        string display_name
        string email UK
        string password_hash
        datetime created_at
    }

    CONSENTS {
        uuid id PK
        uuid user_id FK
        string version
        datetime accepted_at
        datetime revoked_at
    }

    QUESTIONNAIRES {
        uuid id PK
        uuid user_id FK
        json answers
        datetime created_at
    }

    DAILY_LIFESTYLE_OBSERVATIONS {
        uuid id PK
        uuid user_id FK
        date date
        float wrinkle_score
        float sleep_hours
        float water_intake_ml
        float outdoor_minutes
        datetime created_at
    }

    DAILY_HEALTH_ENTRIES {
        uuid id PK
        uuid user_id FK
        date local_date
        string timezone
        int sleep_duration_minutes
        int water_intake_ml
        int outdoor_exposure_choice
        float sleep_score_0_100
        string sleep_score_method
        float predicted_thirst_score_0_10
        float predicted_dryness_score_0_10
        string prediction_status
        string prediction_model_id
        string data_source
        float reported_thirst_score_0_10
        float reported_dryness_score_0_10
        datetime created_at
        datetime updated_at
    }

    ANALYSES {
        uuid id PK
        uuid user_id FK
        string status
        string object_key UK
        string content_type
        float image_quality_score
        json quality_flags
        string model_family
        string model_version
        json result
        string error_category
        datetime created_at
        datetime completed_at
    }

    ANNOTATION_TASKS {
        uuid id PK
        uuid analysis_id UK
        uuid user_id FK
        string object_key UK
        int label_studio_task_id
        datetime expires_at
    }

    TRAINING_RUNS {
        uuid id PK
        string model_family
        string dataset_uri
        string status
        string mlflow_run_id
        json config
        datetime created_at
    }

    INFERENCE_RUNS {
        uuid id PK
        string model_family
        string model_uri
        json input_data
        string status
        json result
        string error_category
        datetime created_at
        datetime completed_at
    }
```

`PK` คือ primary key, `FK` คือ foreign key, `UK` คือ unique key. ความสัมพันธ์ทั้งหมดที่ลากเส้นอยู่ในแผนภาพมี foreign key ไปยัง `users.id` จริง ส่วน `training_runs` และ `inference_runs` ไม่มี foreign key ไปยังตารางอื่น

- `accounts.user_id` เป็น unique: ผู้ใช้หนึ่งคนมีบัญชีได้ไม่เกินหนึ่งบัญชี และผู้ใช้ที่สร้างแบบไม่สมัครอาจไม่มีบัญชี
- `daily_lifestyle_observations` บังคับ unique `(user_id, date)`; `daily_health_entries` บังคับ unique `(user_id, local_date)`
- `annotation_tasks.analysis_id` อ้างถึง `analyses.id` ในโค้ดและเป็น unique แต่ **ไม่ได้ประกาศ foreign key** ในฐานข้อมูล จึงไม่ได้ลากเส้น FK ในภาพ
- คำตอบตอนสมัคร เช่น `outdoor_minutes` อยู่ใน `questionnaires.answers` (JSON); ข้อมูลรายวันใน `daily_health_entries` ใช้ `outdoor_exposure_choice` (ช่วงเวลา 1–4) แทนจำนวนนาที
- ภาพและ artifacts อยู่ใน MinIO โดยตาราง `analyses` และ `annotation_tasks` เก็บเพียง `object_key`
