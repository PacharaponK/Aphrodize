# การปฏิบัติงานด้าน observability

stack เสริมเพิ่ม Prometheus, Loki, Alloy, Grafana Alerting (Discord), metric ของโฮสต์, HTTP probe และ metric ของ GPU แบบเลือกเปิด แอปยังใช้ local log driver ของ Docker การเริ่มแอปตามปกติไม่ขึ้นกับบริการเหล่านี้
ห้ามนำภาพส่วนตัว payload สุขภาพ cookie, authorization header, URL/query ดิบ, SQL หรือข้อความ exception เข้า telemetry request/job ID เป็น metadata สำหรับเชื่อมโยงเหตุการณ์ ไม่ใช่ label ของ metric

## การตั้งค่า deployment

คัดลอกค่าจาก `docker/observability/.env.example` ไป `.env` ส่วนตัวของ deployment สร้าง `OBS_GRAFANA_PASSWORD` ที่ไม่ซ้ำ ใส่ webhook ของช่อง Discord ใน `DISCORD_WEBHOOK_URL` **ในไฟล์ส่วนตัว** ห้ามใส่ใน Git หรือแชต Grafana ใช้
[Discord contact point ในตัว](https://grafana.com/docs/grafana/latest/alerting/configure-notifications/manage-contact-points/integrations/configure-discord/).
จนกว่าจะมี webhook ระบบจงใจให้ contact point ล้มเหลวที่ local loopback; dashboard/การประเมิน alert ทำงาน แต่ยังไม่ยืนยันการส่งถึงผู้รับ

ตั้งฟีเจอร์ deployment อย่างชัดเจน:

| การตั้งค่า | VM ที่ไม่มี worker | stack AI ในเครื่อง | VM ที่มี GPU worker |
| --- | --- | --- | --- |
| `OBS_EXPECTED_QUEUES` | เว้นว่าง | `inference,training` | `inference` |
| `OBS_MINIO_REQUIRED` | `true` | `true` | `true` |
| `OBS_UV_ENABLED` | `true` หากให้บริการ UV snapshot | ขึ้นกับงาน | ขึ้นกับงาน |
| `OBS_CADDY_ENABLED` | `true` | `false` | `true` |
| `OBS_FRONTEND_ENABLED` | `true` | `false` เว้นแต่ frontend อยู่ใน Compose | `true` |

สำหรับ stack ขั้นต่ำในเครื่องที่ไม่มี MinIO ให้ตั้ง `OBS_MINIO_REQUIRED=false` และปิด flag ของ UV, Caddy และ frontend หากไม่มีบริการนั้น worker ที่ควรทำงานแต่หยุดต้องแจ้งเตือน ส่วน worker ที่ตั้งใจปิดไม่ควรแจ้งเตือน สร้างไฟล์ target ของ worker เฉพาะคิวที่คาดว่าจะใช้งาน GPU/DCGM target ต้องเลือกเปิด พอร์ตส่วนตัว 9100 ของ Caddy เผยแพร่ metric โดยไม่เปิด administration API

render การตั้งค่า scrape จาก environment file เดียวกับที่ Compose ใช้:

```powershell
uv run --locked python scripts/configure_observability.py --env-file .env
docker compose --env-file .env -f compose.vm.yml -f compose.observability.yml config --quiet
docker compose --env-file .env -f compose.vm.yml -f compose.observability.yml up -d --build
```

หากใช้ release หรือ DuckDNS overlay ให้คงไว้ในคำสั่ง Compose เดียวกันตามลำดับเดิม แล้วเพิ่ม observability overlay อิมเมจ digest ของ release ต้องมีโค้ดนี้ด้วย การเพิ่ม overlay กับ API image เก่าไม่ได้เพิ่ม instrumentation
หลังเปลี่ยนข้อมูลรับรอง/target ของ API ให้ render ใหม่และ restart Prometheus ไดเรกทอรี `.observability/` ที่ render ถูก Git ละเว้น บน Linux ไดเรกทอรีมีสิทธิ์ 0700; ผู้ใช้คอนเทนเนอร์ Prometheus ต้องอ่านไฟล์รหัสผ่านที่ mount ได้ บน Windows ให้ป้องกันไดเรกทอรีเทียบเท่าด้วย ACL ของเจ้าของ ห้ามพิมพ์ Compose config ที่ render แล้วและมี environment secrets

สำหรับ stack AI ในเครื่อง:

```powershell
docker compose --profile ai --profile background -f compose.yml -f compose.observability.yml -f compose.observability-workers.yml up -d --build
```

deploy worker ที่อัปเดต **ก่อน** API producer ที่อัปเดต: worker รุ่นเก่าไม่รับ correlation metadata ใหม่ ยังรองรับ cron และ job เก่าในคิวที่ไม่มี metadata worker ที่ติด instrumentation แต่ละตัวเปิดพอร์ต 9101 ภายในเท่านั้น และใช้ Redis health key ของ ARQ ทุก 30 วินาที หากเพิ่มจำนวน worker ให้กำหนด target/heartbeat key แยกกัน ปัจจุบัน heartbeat แทน worker pool หนึ่งชุดต่อคิว ไม่ใช่ทุก replica

## การคง observability ใน CI/CD

หลังรวม deployer ที่รองรับเข้า `main` ให้ตั้ง repository variable:

```text
VM_COMPOSE_OVERLAYS=compose.vm-worker-access.yml,compose.duckdns.yml,compose.observability.yml,compose.observability-web.yml
```

บริการ monitoring ต้องติดตั้งและทำงานอยู่ก่อน โดยใช้ Compose project และไดเรกทอรีเดียวกับ VM deployer อ่าน overlay และค่าตั้งส่วนตัวเดิม อัปเดตเฉพาะ API/frontend และคงคอนเทนเนอร์ monitoring, volume, provisioning และบัญชี Grafana ไว้ preflight ปฏิเสธการเปลี่ยนโครงสร้าง monitoring เดิมหรือปิด API telemetry และคงค่าการเชื่อมต่อ annotation เดิม

CI ตรวจ API image ว่ามี metrics route และ collector metrics หลัง deploy ต้องตรวจ metrics โดยยืนยันตัวตน มี collector ที่สำเร็จภายใน 120 วินาที และผ่าน Grafana HTTPS health endpoint มี retry สั้นเพื่อรองรับการเริ่มระบบหรือรอบเก็บข้อมูลของ rollback image เดิม หากล้มเหลวจะคืนค่าตั้งแอปก่อนหน้าโดยไม่ restart monitoring หรือลบ volume การ recovery/rollback ใช้การตรวจเดียวกันและคงประวัติ release เดิม

ตรวจ regression ด้วย `uv run --locked python -m pytest tests/test_observability.py tests/test_observability_readiness.py tests/test_vm_deployment.py` การทดสอบ deployment ใช้ Docker/curl จำลองบน Linux ครอบคลุม success, preflight rejection, health failure, rollback และ recovery โดยไม่หยุดบริการ production

## การเข้าถึงและงบทรัพยากร

หากต้องการเข้าผ่านเบราว์เซอร์ด้วยชื่อโฮสต์ HTTPS เดิมของ VM ให้เพิ่ม `compose.observability-web.yml` หลัง monitoring overlay ตัวอย่างเมื่อใช้ DuckDNS:

```bash
docker compose --env-file .env -f compose.vm.yml -f compose.duckdns.yml -f compose.observability.yml -f compose.observability-web.yml up -d --build
```

เปิด `https://<VM_HOST>/grafana/` และเข้าสู่ระบบด้วย `OBS_GRAFANA_USER` และ `OBS_GRAFANA_PASSWORD` จาก `.env` ส่วนตัวของ VM Caddy คง subpath ไว้ และ Grafana ให้บริการผ่าน
[การตั้งค่า subpath ในตัว](https://grafana.com/tutorials/run-grafana-behind-a-proxy/).
ยังต้องอยู่ในเครือข่ายมหาวิทยาลัย/VPN ตามข้อกำหนดเดิม ตรวจ routing, login, asset และการป้องกัน API ที่ยังไม่ยืนยันตัวตนด้วย `python scripts/check_observability_web.py --url https://<VM_HOST>/grafana/`
สำหรับ release อัตโนมัติ ให้เพิ่ม monitoring overlay ทั้งสองใน `VM_COMPOSE_OVERLAYS` หลัง overlay เดิม เพื่อให้ release API ถัดไปคง telemetry ไว้ deploy `scripts/deploy_vm.py` และซอร์ส monitoring ที่อัปเดตก่อนเปลี่ยนตัวแปรนั้น เพราะ deployer เก่าบน main ปฏิเสธชื่อ overlay เหล่านี้

deployment บน VM วันที่ 2026-10-07 ให้บริการ `/grafana/` พร้อม dashboard System, Jobs และ UV การตรวจจริงผ่านทั้ง scrape target แปดรายการ การเก็บข้อมูล API และการรับข้อมูล Loki อิมเมจ API `aphrodize-api:observability-web` ต่อยอดอิมเมจที่รันอยู่ด้วย HTTP/readiness/UV instrumentation โดยคงการเปลี่ยนแปลงแอปเดิม
GPU และ worker instrumentation ยังไม่ได้เชื่อมต่อ และยังไม่ตั้งการส่ง Discord แผง Jobs ที่ต้องใช้ metric ของ worker จึงไม่มีข้อมูลจริง release อัตโนมัติยังใช้ overlay เดิม ให้เปิด monitoring overlay หลังรวมโค้ดนี้ และอัปเดต worker ก่อน API producer

ใช้ `ssh -N -L 3001:127.0.0.1:3001 operator@vm` แล้วเปิด `http://localhost:3001` เพื่อเข้าสู่ Grafana Prometheus (9090) และ Loki (3100) bind กับ loopback ของโฮสต์เพื่อดูแลระบบ/ทำ tunnel ห้ามเผยแพร่พอร์ต monitoring ที่ไม่มีการยืนยันตัวตนสู่อินเทอร์เน็ต ปิด anonymous access และ signup ของ Grafana ไว้ metric และ readiness ของ API ใช้ Basic authentication ของบริการเดิม

metric เก็บ 15 วัน จำกัด TSDB 2 GB; Loki เก็บ 7 วัน named volume ถาวรเก็บ dashboard/สถานะข้ามการ restart การรับข้อมูลของ Loki จำกัด 2 MB/s พร้อม embedded cache 64 MB ขีดจำกัดหน่วยความจำรวมของ stack ประมาณ 2 GB; วัดทรัพยากรที่เหลือจริงก่อน deploy ร่วมกับ inference metric โฮสต์ของ Docker Desktop อธิบาย Linux VM ของมัน ไม่ใช่เครื่อง Windows
Loki มีระยะเวลาเก็บข้อมูล **ไม่ใช่โควตาดิสก์แบบตายตัว** จึงต้องจัด filesystem/โควตาสำหรับ log และติดตาม filesystem นั้น ห้ามลบ volume ของแอปหรือฐานข้อมูลเพื่อแก้ monitoring alert การลบตาม retention ทำงานแบบ asynchronous

Docker socket proxy ยอมรับ GET สำหรับ metadata ของคอนเทนเนอร์/เครือข่ายและ log แต่ปฏิเสธ POST เข้าถึงได้เฉพาะ Alloy บนเครือข่าย collector ภายใน โดยไม่ mount Docker socket ใน Alloy สิทธิ์ GET ยังเผย metadata ของคอนเทนเนอร์ จึงจำกัดการเข้าถึงทั้งสองบริการ Alloy เก็บเฉพาะ Compose project และบริการแอปที่ติด instrumentation ตามที่ตั้งไว้ ทิ้ง record จากไลบรารีที่ไม่ใช่ JSON และสร้างข้อมูลใหม่จาก field ที่อนุญาตก่อนส่ง log ไป Loki

## GPU worker บนอีกเครื่อง

รวม `compose.gpu.yml` กับ `compose.gpu-observability.yml` โดยใช้ `.env.gpu` ส่วนตัวเดิม เปิด profile `gpu-metrics` เฉพาะเมื่อการตรวจ NVIDIA toolkit/DCGM ก่อนใช้งานผ่านแล้ว คงกฎความปลอดภัย `restart: no` ของ inference ไว้ ตั้ง `LOKI_URL` สำหรับ GPU Alloy; ให้การสื่อสารทั้งหมดอยู่ใน SSH tunnel ส่วนตัวหรือเครือข่าย TLS ที่ยืนยันตัวตน

ตัวอย่าง tunnel บน Linux (เปลี่ยน address/ผู้ใช้ และใช้ SSH key ที่อนุมัติแล้ว):

1. บน VM หา host gateway ของ Docker ด้วย
   `docker network inspect bridge --format '{{(index .IPAM.Config 0).Gateway}}'`.
   bind local forward ของ SSH กับ **gateway นั้นเท่านั้น**:
   `ssh -N -L <VM_DOCKER_GATEWAY>:19101:127.0.0.1:9101 -L <VM_DOCKER_GATEWAY>:19400:127.0.0.1:9400 operator@gpu`.
   จำกัด listener เหล่านี้ด้วย firewall ให้เฉพาะเครือข่าย monitoring
2. ตั้ง `OBS_INFERENCE_TARGET=host.docker.internal:19101` และหากเปิด DCGM ให้ตั้ง
   `OBS_GPU_TARGET=host.docker.internal:19400` บน VM แล้ว render ใหม่และ restart Prometheus
3. บนโฮสต์ GPU สร้าง outbound tunnel ในทิศทางกลับกัน:
   `ssh -N -L <GPU_DOCKER_GATEWAY>:13100:127.0.0.1:3100 operator@vm`.
   ตั้ง `LOKI_URL=http://host.docker.internal:13100/loki/api/v1/push` ใน `.env.gpu`.
   จำกัด listener นี้ด้วย firewall ให้เฉพาะ GPU Alloy ดูแลโปรเซส SSH; เมื่อ tunnel หายควรมี alert ของ exporter/heartbeat หรือการส่ง log

ไม่มีการเตรียมข้อมูลรับรอง SSH หรือสิทธิ์เข้าถึง GPU ให้อัตโนมัติ หาก Docker ตั้ง host-gateway เอง ให้ใช้ address จริงนั้นให้ตรงกันทั้ง listener และ target

## ความหมายของสถานะและ dashboard

`/api/v1/health` ตรวจ liveness เท่านั้น `/api/v1/monitoring/ready` ตรวจ `SELECT 1`, Redis PING และการมีอยู่ของ MinIO bucket โดยยืนยันตัวตน พร้อม timeout สั้น ส่งคืน capability และสถานะ dependency โดยตอบ HTTP 503 เมื่อบริการบัญชี/ฐานข้อมูลไม่พร้อม
เมื่อ storage/queue ล้มเหลวแต่บริการบัญชียังพร้อม จะได้ `degraded` ความพร้อมส่ง job ไม่ยืนยันว่า worker/โมเดลพร้อม ให้ดู metric heartbeat ของ worker ที่คาดว่าจะใช้งาน readiness ทำงานแยกจาก Prometheus/Grafana

| Dashboard | สิ่งที่ควรตรวจ |
| --- | --- |
| System | probe ของ API/frontend, metric ของ route, การตรวจ dependency, CPU/RAM/ดิสก์, ความสดของ telemetry |
| Jobs | heartbeat ที่คาดหวัง, แถว workflow หลักที่เข้าคิว, p95 ของเวลารอ/ประมวลผล, ผลงาน, หน่วยความจำ GPU |
| UV | ความพร้อมใช้พยากรณ์, อายุ snapshot, ความสด/alert ของรายงานคุณภาพ |

gauge ของคิวรวมแถว `queued` จาก Analysis, InferenceRun และ TrainingRun โดยไม่ดึง payload จึงตรวจแถวตกค้างที่บันทึกไว้ได้แม้ Redis job หายไปแล้ว ไม่รวม job ล้างข้อมูล/annotation แบบเลื่อนเวลา และ singleton ฝึก cohort ใน gauge เหล่านี้ แต่ยังส่ง metric/log ของ job เมื่อรัน
อายุแถวที่กำลังรันนับจากเวลาส่ง เพราะ schema ปัจจุบันไม่มี timestamp เริ่มประมวลผล histogram ของการประมวลผลวัดเวลาทำงานจริงแยกต่างหาก เพิ่ม query สถานะ/เวลาสร้างที่มี index หากการเก็บข้อมูลใช้เวลาเกิน timeout 3 วินาทีเมื่อข้อมูลมากขึ้น

job `failed` แยกจากภาพ `rejected`; ความล้มเหลวทางธุรกิจที่จัดการภายในต้องระบุผล job อย่างชัดเจน counter ของ job นับความพยายาม รวม retry/ยกเลิก ไม่ใช่จำนวนการวิเคราะห์ผู้ใช้ที่ไม่ซ้ำ ความสด UV ใช้ snapshot และรายงาน monitoring เดิมที่ตรวจแล้ว การปิด UV monitoring ระงับ alert ของมัน
การรายงานคุณภาพโมเดลยังอยู่ใน MLflow และ monitoring API เดิม telemetry สำหรับปฏิบัติการไม่ได้ยืนยันความแม่นยำโมเดล

ใน Grafana Explore เลือก Loki แล้ว query:

```text
{service=~"api|frontend|inference-worker|trainer-worker"} | json | request_id="<32-hex-id>"
```

หา `job_enqueued` แล้วตาม `job_id` ไป `job_started`/`job_finished` log ของ exception เก็บชนิดและตำแหน่งโค้ดที่ปลอดภัย โดยทิ้งข้อความ พารามิเตอร์ SQL และตัวแปร local

## alert และการตอบสนอง

เตรียมกฎจาก `docker/observability/grafana/alerting/rules.yml` แก้ threshold ทดลองใน `scripts/generate_observability_dashboards.py` แล้วรันสคริปต์เพื่อสร้าง dashboard/กฎใหม่และ restart Grafana ทรัพยากรที่ provision จงใจให้อ่านอย่างเดียวใน UI

| alert | threshold ทดลอง | การตอบสนองและตรวจการกู้คืน |
| --- | --- | --- |
| API/probe หยุด | 2 นาที | ตรวจโปรเซส/เครือข่าย แล้วตรวจ liveness และ readiness |
| dependency ที่จำเป็นหยุด | 2 นาที | ตรวจบริการ/การยืนยันตัวตนที่ระบุ กู้คืนโดยไม่ลบ volume |
| worker/exporter ที่คาดหวังหาย | 2 นาที | ตรวจโปรเซส Redis, tunnel ส่วนตัว และการตั้งค่าโมเดลที่ผ่านการตรวจ |
| คิว inference ค้าง | งานเก่าสุดรอ >5 นาที ต่อเนื่อง 2 นาที | หา log ของ job; ตรวจ DB/Redis ให้ตรงกันก่อน retry |
| คิว training ค้าง | งานเก่าสุดรอ >1 ชั่วโมง ต่อเนื่อง 5 นาที | ตรวจ trainer และระยะเวลาของงาน |
| inference รันเกินเวลา | อายุแถว >15 นาที ต่อเนื่อง 2 นาที | แยกเวลารอคิวจากเวลาประมวลผล และตรวจแก้สถานะหลัง crash |
| retention/annotation staging ล้มเหลว | มีความล้มเหลวใน 5 นาที | ตรวจงานที่ระบุและแก้ artifact หรือ annotation staging แม้ inference สำเร็จ |
| API/frontend ผิดพลาด | 5xx >5% เมื่อมี ≥20 request ใน 5 นาที ต่อเนื่อง 5 นาที | ระบุ route/request กู้ upstream และตรวจว่าอัตราผิดพลาดลดลง |
| ดิสก์ใกล้เต็ม | ว่าง <15% นาน 10 นาที | ตรวจการโตของ log/artifact และ retention ที่อนุมัติ ยืนยันพื้นที่เหลือ |
| collector ล้มเหลว/ข้อมูลเก่า | ล้มเหลวหรือเก่า >120 วินาที ต่อเนื่อง 2 นาที | ตรวจ `collector_failed`, SQL/Redis; ยืนยันว่า timestamp เดินต่อ |
| UV ไม่พร้อม/ข้อมูลเก่า | >8 ชั่วโมงหรือวันที่ไม่ถูกต้อง ต่อเนื่อง 5 นาที | ตรวจ log รีเฟรช snapshot และ pointer ที่ใช้ให้บริการ |
| คุณภาพ UV ต้องตรวจ | รายงานคุณภาพเก่า/หาย/มี alert ต่อเนื่อง 5 นาที | ตรวจรายงาน monitoring และคงการอนุมัติโมเดลด้วยตนเอง |

notification จัดกลุ่มตาม alert/dependency/queue รอ 30 วินาที อัปเดตกลุ่มทุก 5 นาที และส่ง alert ที่ยังไม่แก้ซ้ำทุก 4 ชั่วโมง Discord รับข้อความ firing และ resolved พร้อมลิงก์ dashboard และแนวทางตอบสนอง ตั้ง `OBS_GRAFANA_URL` เป็น URL ที่ผู้ปฏิบัติการเข้าถึงได้จริง; ลิงก์ localhost ต้องใช้ SSH tunnel ของผู้ปฏิบัติการ
ใช้ Grafana Contact points → operations → Test เพื่อตรวจ **ช่องจริง** แล้วซ้อมความล้มเหลวและกู้คืนแบบควบคุมใน staging การบันทึก webhook อย่างเดียวไม่ยืนยันการส่ง

## ข้อจำกัดของ probe อิสระ

ปัจจุบัน **ไม่มีเครื่องอิสระ** สำหรับ external probe monitoring บน VM ส่ง alert ไม่ได้เมื่อ VM/เครือข่าย/ไฟฟ้าล้มเหลวทั้งระบบ นี่เป็นช่องว่างด้านปฏิบัติการที่ยังเหลืออยู่ เมื่อมีโฮสต์/provider อื่น ให้รัน `compose.external-probe.yml` ที่นั่นด้วย `PROBE_URL=https://<domain>/api/health` และ Discord webhook ของมัน
probe ตรวจ HTTPS และ JSON liveness เก็บสถานะ ส่งครั้งเดียวเมื่อเปลี่ยนเป็นล่ม/กู้คืน และ retry การส่งที่ล้มเหลว การตรวจทุก 30 วินาทีล้มเหลวสี่ครั้งเท่ากับประมาณสองนาที ขั้นตอนนี้ตรวจ liveness ของ frontend; probe API ภายใน/alert ของ dependency ครอบคลุม backend ไม่ใช่การทดสอบ login จำลองหรือ image inference ป้องกันไฟล์ webhook และดูแลตัว probe ด้วย

## การตรวจสอบและ rollback

```powershell
uv run --locked python -m pytest tests/test_observability.py
uv run --locked python -m scripts.test_observability_stack
.\scripts\check-health.ps1 -ComposeFiles compose.vm.yml,compose.observability.yml
```

การตรวจ Docker สร้างเฉพาะ `aphrodize-observability-check` ใช้ metric สังเคราะห์และตัวรับในเครื่องที่เข้ากับ Discord ตรวจการ provision Grafana, scrape Prometheus, การกรองข้อมูลส่วนตัวจาก Docker local-driver → Alloy → Loki, การส่ง firing/recovery และการเก็บสถานะข้าม restart แล้วลบคอนเทนเนอร์/volume ชั่วคราวของโครงการทดสอบนั้น
ไม่ได้ทดสอบฮาร์ดแวร์ GPU ของ production, Discord จริง หรือการเข้าถึง VM จริง

ใน staging ให้ลองหยุด worker, ขัดจังหวะ Redis, ทำ UV snapshot ให้เก่า และหยุด Alloy แล้วตรวจ alert และ notification ว่าแก้ไขแล้วให้ตรงกัน ห้ามซ้อมกับงานผู้ใช้จริงโดยไม่กำหนดเวลาขัดจังหวะ เก็บ baseline เจ็ดวันก่อนตั้งเป้าหมาย latency/availability ของ production ไม่สามารถอ้าง baseline เจ็ดวันจากการรันเพื่อพัฒนา

หากต้องการปิดการเก็บข้อมูล ให้ตั้ง `OBSERVABILITY_ENABLED=false` และหยุดเฉพาะบริการ monitoring เก็บ volume monitoring หากต้องการประวัติ หาก rollback instrumentation ให้คืนอิมเมจแอปก่อนหน้า ห้ามลบข้อมูล PostgreSQL, Redis หรือ MinIO
รุ่นแรกนี้ยังไม่ deploy ที่เก็บ distributed tracing; correlation ID เชื่อม request/job สำคัญอยู่แล้ว และต่อยอดเป็น trace context ได้เมื่อจำเป็น
