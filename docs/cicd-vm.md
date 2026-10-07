# CI/CD ใน repository Aphrodize เดิม

ทุกส่วนอยู่ใน PacharaponK/Aphrodize โดย CI และการ build อิมเมจรันบน runner ที่ GitHub จัดให้ ส่วน deployment รันบน self-hosted runner ของ repository บน VM เจ้าของยอมรับอย่างชัดเจนให้ใช้ repository สาธารณะกับ self-hosted runner ไม่ต้องมี repository ที่สองหรือ token ข้าม repository

## ขั้นตอน release

merge dev เข้า main ที่มีการป้องกัน → Backend/Frontend CI ของ commit นั้นผ่าน → workflow Release build API, frontend และ MinIO → อัปโหลด manifest ของ GHCR digest → runner ของ production อัปเดต API/frontend → ตรวจ health/readiness/HTTPS → สำเร็จ

CI ที่ล้มเหลว การรันจาก PR/dev/fork และ candidate ของ main ที่ถูกแทนที่แล้วไม่สามารถเข้าสู่ขั้นตอน release ของ production ได้ ต้องเผยแพร่อิมเมจทั้งหมดก่อนจึงมี manifest การปิด deploy job ไม่ขัดขวางการเผยแพร่ MinIO ถูกเผยแพร่สำหรับ bootstrap/โครงสร้างพื้นฐาน แต่ release แอปตามปกติไม่อัปเดต PostgreSQL, Redis, MinIO หรือ Caddy

manifest บันทึก schema_version=1, source_sha, run_id, site_url และ images การ deploy ใช้การอ้างอิง image@sha256 ส่วน SHA tag ใช้ค้นหาอิมเมจเท่านั้น artifact เก็บ manifest ครบ 90 วัน; VM เก็บการตั้งค่าปัจจุบัน ก่อนหน้า และประวัติไว้เป็นส่วนตัวโดยไม่ขึ้นกับการหมดอายุของ artifact

## การตั้งค่า repository (เจ้าของ)

ใน Settings → Secrets and variables → Actions → Variables ให้ตั้งค่า:

| ตัวแปร | ค่า |
| --- | --- |
| SITE_URL | `https://aphrodize.duckdns.org` (ต้องตรงกับ VM_HOST ของ production) |
| VM_DEPLOY_ENABLED | เริ่มด้วย `false`; `true` เปิด deployment ของ production อัตโนมัติ |
| VM_DEPLOY_DIR | ไดเรกทอรี production แบบ absolute ที่คงที่ เช่น `/home/aphrodize/Aphrodize` |
| VM_COMPOSE_OVERLAYS | `compose.duckdns.yml` หากใช้ DuckDNS; ต่อท้าย `,compose.vm-worker-access.yml` เฉพาะเมื่อใช้อยู่แล้ว |
| VM_TLS_CA_FILE | path แบบ absolute ของไฟล์ใบรับรอง CA สาธารณะ หากใช้ TLS ภายในของ Caddy; มิฉะนั้นไม่ต้องตั้ง |

VM_DEPLOY_ENABLED ต้องเป็น **ตัวแปรระดับ repository** เพราะ GitHub ตรวจค่าก่อนจัดตาราง job ของ production ตัวแปร VM อื่นเป็นตัวแปรระดับ repository หรือ environment ของ production ได้ ห้ามใส่รหัสผ่าน runtime ใน variables

สร้าง Settings → Environments → production และจำกัดสาขา deployment เป็น main รักษาการป้องกัน main และการตรวจ CI ที่บังคับไว้ การกำหนด reviewer อนุมัติเป็นทางเลือก และจะพัก deployment อัตโนมัติจนได้รับอนุมัติ ตรวจว่าผู้ร่วมงานคนใดแก้ workflow และอนุมัติการรัน workflow จาก fork ได้ label ของ runner ใช้กำหนดเส้นทางงาน ไม่ใช่ขอบเขตแยกสิทธิ์ ความเสี่ยงของ runner ใน repository สาธารณะที่ยอมรับไว้ยังคงอยู่ เงื่อนไข event ของ workflow นี้ไม่สามารถจำกัด workflow อื่นได้

job ของ workflow ใช้ GITHUB_TOKEN สำหรับ GHCR: packages:write เฉพาะตอนเผยแพร่ และ packages:read ตอน deploy ไม่ต้องมี PAT ใหม่สำหรับ package ที่ workflow ของ repository นี้สร้าง หาก package GHCR เดิมปฏิเสธการเข้าถึง ให้ให้สิทธิ์ Actions ของ repository นี้ใน settings ของ package
คง visibility ของ package เป็น private เว้นแต่เจ้าของตั้งใจเผยแพร่เนื้อหาอิมเมจ repository ซอร์สสาธารณะไม่ได้บังคับให้อิมเมจเป็นสาธารณะ

## ติดตั้ง runner บน VM (เจ้าของ)

ติดตั้ง runner บน VM เดิมเพื่อให้ deploy job ใช้ Docker ในเครื่องได้ ใช้บัญชี runner เฉพาะที่อ่านการตั้งค่า production และเขียนไดเรกทอรี `.releases` ของ production ได้ อย่าเก็บเนื้อหา .env ของแอปในซอร์ส การเข้าถึง Docker daemon เทียบเท่าสิทธิ์ระดับโฮสต์ อย่าปะปน workspace ของ runner กับไดเรกทอรี production ที่คงที่

สิ่งที่ต้องมี: Linux x64, Docker, Compose v2 ที่รองรับ `--wait` และ JSON config, Bash, Python 3, curl, flock, Git และ dependency ของ GitHub runner ตรวจด้วย:

```bash
docker version
docker compose version
python3 --version
curl --version
command -v flock
```

Docker ต้องทำงานโดยไม่ถามรหัสผ่าน sudo **เมื่อใช้บัญชี runner** จัดการสิทธิ์ Docker/บัญชีอย่างชัดเจน อย่าใส่ `sudo` ในคำสั่ง workflow แทนการเตรียมสิทธิ์ runner ต้องเข้าถึง GitHub, บริการ artifact ของ Actions, GHCR และชื่อโฮสต์ production ผ่าน HTTPS ขาออกได้ ไม่ต้องเปิด SSH ขาเข้าสาธารณะหรือมี public address ของ VM

เปิด Settings → Actions → Runners → New self-hosted runner → Linux → x64 ทำตามคำแนะนำดาวน์โหลด/ตรวจ checksum/ติดตั้งที่ GitHub แสดงในปัจจุบัน โดยใช้ไดเรกทอรีเฉพาะ เช่น `/opt/aphrodize-runner` ลงทะเบียนด้วย:

- URL ของ repository: https://github.com/PacharaponK/Aphrodize
- ชื่อ: aphrodize-vm
- label เพิ่มเติม: aphrodize-deploy
- ไดเรกทอรีทำงาน: `_work` ภายในไดเรกทอรี runner เฉพาะ

ใช้ registration token อายุสั้นเฉพาะบน VM ห้ามวางในแชต commit หรือบันทึกใน `.env` ติดตั้ง runner เป็น service ด้วย `svc.sh` ที่ GitHub ให้ โดยรันภายใต้บัญชี runner เฉพาะ เปิดการอัปเดต runner อัตโนมัติไว้ ยืนยันว่าแสดง Online/Idle ใน settings ของ repository ก่อนเปิด deployment

## ไดเรกทอรี production และสถานะตั้งต้นครั้งแรก

VM_DEPLOY_DIR ชี้ไปไดเรกทอรีที่ใช้ compose.vm.yml อยู่แล้ว คง `.env` เดิม (สิทธิ์ 600), Compose overlay, ไฟล์ docker/Caddyfile และ storage/artifacts/uv ที่ mount ไว้ ให้บัญชี runner เข้าถึงไฟล์เดิมและสถานะ release ส่วนตัวเท่าที่จำเป็นเท่านั้น อย่าคัดลอก .env ไป checkout ของ Actions หรือ artifact ตั้ง VM_COMPOSE_OVERLAYS ตาม overlay ที่ใช้งานจริง เพื่อรักษาใบรับรอง DuckDNS และพอร์ต worker

การ deploy ครั้งแรกบันทึก image ID ของ api/frontend ที่กำลังทำงานและ healthy พร้อม Compose configuration ปัจจุบันที่ render ครบก่อนอัปเดต รวมถึงอิมเมจในเครื่อง `aphrodize-api:vm`/`aphrodize-frontend:vm` จึง rollback ครั้งแรกได้โดยไม่ต้องใช้ registry tag เก่า หากไม่มีบริการหรือบริการไม่ healthy จะ bootstrap ไม่ได้

การตั้งค่าที่ render มีข้อมูลรับรอง runtime จึงจงใจเขียนเฉพาะ VM_DEPLOY_DIR/.releases (ไดเรกทอรีสิทธิ์ 700; ไฟล์สิทธิ์ 600) ห้ามอัปโหลดหรือวางไฟล์เหล่านี้ใน log ของ Actions, issue หรือแชต Release-manifest.json มีเฉพาะการอ้างอิงอิมเมจและที่มาของซอร์ส ไม่มีข้อมูลรับรอง production

การ render Compose ของ candidate ใช้ไดเรกทอรี production ที่คงที่อย่างชัดเจนสำหรับทุก host path ชื่อ persistent volume และการตั้งค่าโครงสร้างพื้นฐานต้องตรงกับการตั้งค่าปัจจุบันที่บันทึกไว้ หากเปลี่ยนต้องเป็นงานโครงสร้างพื้นฐานแยกที่ผ่านการตรวจ ไฟล์ Caddy configuration ในไดเรกทอรีคงที่ยังจัดการโดยผู้ปฏิบัติการ เพราะ release ตามปกติไม่สร้าง Caddy ใหม่

ตรวจ URL `/login` ภายนอกก่อน สำหรับ TLS ภายใน ให้ส่งใบรับรอง CA สาธารณะผ่าน VM_TLS_CA_FILE ห้ามปิดการตรวจใบรับรอง สคริปต์ deploy ยังตรวจ PostgreSQL SELECT 1, Redis PING และ MinIO bucket ที่จำเป็นทั้งสอง โดยใช้ runtime settings ของ API; การตรวจ liveness เพียงอย่างเดียวไม่พอ

## deployment ครั้งแรกและ release อัตโนมัติหลังจากนั้น

1. merge implementation ที่ตรวจแล้วเข้า main โดยยังปิด deployment ไว้
2. รอ CI ของ main และ build อิมเมจ release ทั้งสาม ตรวจ artifact `release-manifest-<SHA>` ของการรัน Release; source SHA และ run ID ต้องตรงกับการรันนั้น
3. ยืนยันว่า runner ของ VM ว่าง การเลือก overlay/origin/CA ถูกต้อง และ API/frontend เดิม healthy สำรองข้อมูล production แยกต่างหาก
4. ตรวจ candidate แรกก่อนตั้ง VM_DEPLOY_ENABLED=true นี่คือขั้นตอนเปิดใช้งาน: release ของ main ที่ผ่านเงื่อนไขหลังจากนี้จะเปลี่ยนบริการ production
5. รัน **ทุก job** ใหม่ของ Release ที่ผ่านเงื่อนไขบน main ปัจจุบัน หรือ merge commit ใหม่ที่ตรวจแล้ว หาก main เปลี่ยนไป การรันเก่าจะถูกปฏิเสธเพราะถูกแทนที่
6. ยืนยันว่า deployment job ผ่าน แล้วทดสอบเข้าสู่ระบบ/ออกจากระบบ/โปรไฟล์จากลูกข่ายที่ได้รับอนุญาตในเครือข่าย VM ตรวจ source SHA ที่เผยแพร่และ deploy
7. ทดลองความล้มเหลวที่ควบคุมได้และ rollback ใน stack ชั่วคราวก่อน การจงใจทดสอบให้ production ล้มเหลวต้องได้รับอนุมัติ candidate อย่างชัดเจน

การอัปเดตดึงอิมเมจก่อน เตรียม bucket ที่จำเป็น แทนที่เฉพาะ API/frontend และรอ health ไม่มีการ build บน VM ไม่มี `compose down`, การลบ volume หรือการ prune อิมเมจใน deployment การสร้างบริการใหม่บน VM เดียวอาจขัดจังหวะ request ชั่วครู่ ปัจจุบัน API เพิ่ม schema ตอนเริ่มระบบ จึงต้องตรวจ migration/ความเข้ากันได้ย้อนหลังก่อน release เพราะ rollback อิมเมจย้อนการเปลี่ยน schema/ข้อมูลไม่ได้

## rollback และการกู้คืน

ใช้สคริปต์จาก checkout ของ release ที่ตรวจแล้ว พร้อม path deployment แบบ absolute หากต้องการ rollback ด้วยตนเองไป release ก่อนหน้าที่บันทึกไว้:

```bash
bash scripts/deploy-vm.sh --rollback --deploy-dir /home/aphrodize/Aphrodize
```

เพิ่ม `--ca-file /absolute/path/to/public-root.crt` สำหรับ TLS ภายใน overlay รวมอยู่ในการตั้งค่าที่บันทึกแล้ว rollback จึงใช้ bundle เดิมทุกประการ lock บนโฮสต์ป้องกันคำสั่ง deploy หรือ rollback ซ้อนกัน

candidate ที่ล้มเหลวจะคืนอิมเมจ/การตั้งค่าก่อนหน้าอัตโนมัติ แล้วตรวจ health อีกครั้ง แม้คืนสำเร็จ deployment job ยังคงเป็นสีแดง candidate ที่ล้มเหลวอยู่ในประวัติ release ส่วนตัวและไม่ถูกเลื่อนเป็นตัวใช้งาน

หาก job ถูกยุติหรือคืนสถานะไม่สำเร็จ ระบบเก็บ pending-release.json และปฏิเสธ deployment ใหม่ หลังตรวจ Docker/health ของบริการในเครื่องแล้ว ลองกู้คืนอีกครั้งด้วย:

```bash
bash scripts/deploy-vm.sh --recover --deploy-dir /home/aphrodize/Aphrodize
```

ใช้ตัวเลือก CA เดิมเมื่อจำเป็น เก็บอิมเมจก่อนหน้าและสถานะ release ไว้ ห้ามรัน `docker image prune -a` หากอิมเมจก่อนหน้าหายไป ให้คืนจาก registry digest ที่บันทึกหรืออิมเมจตั้งต้นที่สำรองแยกไว้ก่อนกู้คืน หากกู้คืนล้มเหลว ผู้ปฏิบัติการต้องเข้าแก้ไข ห้ามลบ pending state เพียงเพื่อให้ job ถัดไปเป็นสีเขียว เก็บ backup ฐานข้อมูล/ที่เก็บข้อมูลแยกจาก rollback อิมเมจ

## หลักฐานการตรวจสอบและการตั้งค่าที่ยังเหลือ

การทดสอบ implementation ในเครื่องใช้ไดเรกทอรีชั่วคราวและคำสั่ง Docker/curl จำลอง ไม่อัปเดต stack จริงบน VM การ smoke test อิมเมจ production และ CI ปกติก็รันในสภาพแวดล้อมชั่วคราว การตั้งค่า ลงทะเบียน runner และเผยแพร่/deploy จริงครั้งแรกเป็นหน้าที่ผู้ดูแล CI ของ dev ที่ผ่านไม่ยืนยันว่าการเผยแพร่ GHCR หรือ deployment ของ production บน main เกิดขึ้นแล้ว

แหล่งอ้างอิง: [workflow_run](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_run),
[การเผยแพร่อิมเมจ](https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images),
[การลงทะเบียน runner](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/add-runners).

ผลตรวจ implementation (2026-10-06): ชุดทดสอบ Python 3.11 ทั้งหมดผ่าน 350 รายการ, frontend ผ่าน 76 รายการ, ESLint/TypeScript/production build ผ่าน, build อิมเมจ production ทั้งสามสำเร็จ, API smoke imports ผ่าน, actionlint และ ShellCheck ผ่าน การตรวจรอบใหม่พบและแก้การรักษาประวัติ rollback พร้อม regression test
การตรวจ Compose configuration จริงครอบคลุม base, DuckDNS และ worker overlay; stack Docker จริงแยกต่างหากผ่าน readiness และล้มเหลวตามคาดเมื่อหยุด Redis การเผยแพร่ registry และ deploy จริงยังไม่ยืนยันจนกว่าเจ้าของจะ merge และทำขั้นตอนตั้งค่าข้างต้นครบ
