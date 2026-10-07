# การตรวจ annotation ริ้วรอย

workflow นี้ให้มนุษย์ตรวจภาพใบหน้าที่จัดแนวแล้วและได้รับความยินยอม ไม่ได้ฝึกโมเดลหรือถือ mask ของโมเดลเป็นข้อมูลจริงอ้างอิง

## ตั้งค่าครั้งแรก

1. เริ่ม Compose stack และสร้าง Label Studio API token ใส่ใน `.env` เป็น `LABEL_STUDIO_API_KEY` แล้ว restart `api` และ `inference-worker` เพื่อให้รับค่า
2. รัน `docker compose exec api python -m backend.scripts.setup_annotation_project` คัดลอก `LABEL_STUDIO_PROJECT_ID` ที่แสดงไป `.env` แล้ว restart `api` และ `inference-worker` อีกครั้ง
3. ทดสอบหนึ่ง task ใน UI ติดป้ายก่อนเก็บภาพผู้ใช้ worker ใส่ภาพที่ได้รับความยินยอมใน MinIO bucket ส่วนตัว `aphrodize-annotation` แล้วส่งไป task ของ Label Studio โดยตรงเป็นภาพ inline ไม่ต้องเชื่อม S3 source storage หรือยกเว้นข้อจำกัดเครือข่ายส่วนตัว วิธีนี้เหมาะกับการทดลองตรวจขนาดเล็ก หากจำนวน task ทำให้โครงการ Label Studio ช้า ให้ย้ายภาพ task ไป external storage

## กฎการตรวจ

- ภาพคือใบหน้าที่จัดแนวแล้วซึ่งโมเดลริ้วรอยใช้ ระบายพิกเซลริ้วรอยที่มองเห็นด้วยแปรง `Wrinkle`; เว้นพิกเซลอื่นไว้ เลือก `Visible wrinkles` หรือ `No visible wrinkles` อย่างชัดเจน ภาพไม่มีริ้วรอยส่งออกเป็น mask ศูนย์ได้; annotation ที่ยังไม่เสร็จใช้ไม่ได้
- ข้ามภาพที่เบลอ ถูกบดบัง จัดแนวผิด หรือระบุ annotation อย่างน่าเชื่อถือไม่ได้ ห้ามอนุมานการวินิจฉัยทางคลินิก
- หากเพิ่ม mask จากโมเดลภายหลัง ให้ถือเป็นคำแนะนำเท่านั้น annotation ของมนุษย์คือผลตรวจ
- ห้ามคัดลอกภาพ ชื่อ หรือคำตอบเข้า comment หรือ log

checkbox ทางเลือกในหน้าถ่ายภาพสร้างความยินยอม `image-annotation-v1` แยกสำหรับการอัปโหลดนั้น จัดเตรียมเฉพาะการวิเคราะห์ที่สำเร็จและยังมีความยินยอม annotation ที่ใช้งานอยู่ ภาพที่จัดแนวและ task ของ Label Studio ถูกกำหนดให้ลบหลัง 30 วัน
หน้าถ่ายภาพเพิกถอนความยินยอมตรวจภาพที่ส่งจากเบราว์เซอร์เดียวกันในช่วงนั้นได้ `DELETE /api/v1/consents/users/{user_id}/annotations` เพิกถอนความยินยอมของผู้ใช้หนึ่งคนและลบข้อมูลตรวจ; `DELETE /api/v1/users/{user_id}/images` รวมการล้างข้อมูลเดียวกัน หาก Label Studio ไม่พร้อมตอนลบ จะลบภาพก่อนและ API ตอบ 503 ให้ retry หลัง Label Studio กลับมาทำงาน worker ยัง retry การล้างข้อมูลค้างทุกชั่วโมง การเพิกถอนผ่านเบราว์เซอร์เท่านั้นนี้เป็นวิธีชั่วคราวจนแอปมีบัญชีผู้ใช้

ไม่มี annotation ใดถูก export หรือใช้ฝึกอัตโนมัติ หน้า `/admin` ส่งออก annotation ที่ผู้ดูแลเลือกและยืนยันการตรวจได้ เฉพาะภาพที่มีความยินยอม `wrinkle-model-training-v1` และ model input ที่เก็บขณะวิเคราะห์ ดู [ขั้นตอนฝึกและอนุมัติรุ่น](Curated-Training.md) การถอนความยินยอมตรวจภาพจะถอนสิทธิ์ฝึกด้วย ส่วนการถอนสิทธิ์ฝึกอย่างเดียวลบ input/snapshot แต่ยังเก็บภาพตรวจตามความยินยอมตรวจที่มีอยู่

## VM and Windows GPU deployment

The VM runs the pinned Label Studio release using the `annotation` Compose profile.
Open `https://<VM_HOST>/label-studio/`; reviewer credentials are kept in the VM's
private `.env` (`LABEL_STUDIO_USERNAME` and `LABEL_STUDIO_PASSWORD`). Public signup
is disabled. Caddy strips the URL prefix before forwarding to Label Studio, while
`LABEL_STUDIO_HOST` generates links with the public prefix. The backend uses the
internal `http://label-studio:8080` URL. Keep the Label Studio named volume: it holds
the reviewer account, project configuration and annotations.

```bash
docker compose -f compose.vm.yml -f compose.vm-worker-access.yml -f compose.duckdns.yml --profile annotation up -d label-studio api
docker compose -f compose.vm.yml -f compose.vm-worker-access.yml -f compose.duckdns.yml --profile annotation up -d --no-deps --force-recreate caddy
```

Recreate Caddy after updating its Caddyfile so the existing container mounts and
loads the new Label Studio route.

Set `LABEL_STUDIO_API_KEY` and `LABEL_STUDIO_PROJECT_ID` in the private VM `.env`.
The startup token uses Label Studio's explicitly enabled legacy-token support;
never place it in browser code or Git. The `Aphrodize wrinkle mask review` project
uses the existing `Wrinkle` brush configuration from `setup_annotation_project.py`.

The remote GPU worker must receive the same project and token. Its
`compose.gpu.yml` no longer overrides them with an empty token and project zero.
The VM prepares `.env.annotation.gpu` with only the three Label Studio settings,
using the public HTTPS URL for Windows. In the existing Windows GPU runtime folder:

```powershell
scp aphrodize@172.30.81.237:~/Aphrodize/scripts/enable-annotation-gpu.ps1 .
powershell -ExecutionPolicy Bypass -File .\enable-annotation-gpu.ps1
```

This script preserves model paths and data-service credentials, updates review
settings, restarts the existing worker image, and checks access to the project.
It does not rebuild the model. Keep `.env.gpu` and `.env.annotation.gpu` private.
After it reports `GPU worker -> Label Studio: OK`, test a newly consented upload:
`completed` analysis -> private aligned image -> queued publish -> Label Studio task.
Only separately consented successful analyses enter review. Review consent does not
permit model training. Revocation deletes both the review copy and the remote task;
retention remains 30 days. Old uploads without review consent are not backfilled.
