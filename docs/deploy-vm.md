# deploy VM ก่อนเชื่อมต่อ GPU worker

ใช้ไฟล์ Compose แยกนี้ VM รัน PostgreSQL, Redis, MinIO, การเตรียม bucket, API, frontend และ Caddy เผยแพร่เฉพาะ HTTPS และ HTTP ที่ redirect ไป HTTPS โดย bind กับ `VM_BIND_IP`
ไม่เริ่ม GPU worker, trainer, MLflow หรือ Label Studio และไม่ใช้ Compose สำหรับพัฒนาหรือ profile `ai`

## การตั้งค่า

เก็บ `.env` เป็นส่วนตัว (สิทธิ์ 600) นอกจากความลับเดิม ให้ตั้งค่า:

```dotenv
VM_HOST=aphrodize.duckdns.org
VM_BIND_IP=172.30.81.237
ANALYSIS_SESSION_SECRET=<unique random secret of at least 32 bytes>
```

เตรียมค่าเหล่านี้ในเครื่องแล้ว ให้ยืนยันว่า VM ยังใช้ IP นี้อยู่

A record ของ DuckDNS สำหรับ `aphrodize.duckdns.org` ต้องระบุ `172.30.81.237` อย่างชัดเจน ห้ามเปิดการตรวจ public IP อัตโนมัติในการตั้งค่าที่ใช้ภายในเท่านั้นนี้ เครื่องลูกข่ายต้องมีเส้นทางเครือข่ายไปยัง VM (เครือข่ายมหาวิทยาลัยหรือ VPN ที่ได้รับอนุญาต) การแบ่งเครือข่ายของมหาวิทยาลัยอาจยังทำให้เข้าถึงไม่ได้ หาก DNS ของมหาวิทยาลัยบล็อกชื่อสาธารณะที่ชี้ไป private IP ให้ขอ IT สร้าง DNS record ภายใน ชื่อโฮสต์ไม่ได้ให้สิทธิ์เข้าถึงเครือข่ายหรือบังคับว่าผู้ใช้ต้องเป็นสมาชิกมหาวิทยาลัย

หลังเปลี่ยน `VM_HOST` ให้ build frontend ใหม่และสร้างเฉพาะบริการเว็บใหม่:

```bash
docker compose -f compose.vm.yml build frontend
docker compose -f compose.vm.yml up -d --no-deps --wait frontend caddy
```
ไฟล์ Compose นี้ตั้ง production อย่างชัดเจน ฟังก์ชันผู้ดูแลยังปิดจนกว่าจะตั้งข้อมูลรับรองผู้ดูแลแยกต่างหาก ความลับเป็น environment variable ตอนรันเท่านั้น ห้ามใช้เป็น frontend build argument หรือตัวแปรในเบราว์เซอร์

## ตรวจสอบ ตรวจความปลอดภัย และเริ่มระบบ

```bash
cd ~/Aphrodize
docker ps
docker compose -f compose.vm.yml config --quiet
docker compose -f compose.vm.yml build
```

ตรวจอิมเมจสำหรับ build ซึ่งมี package manager ที่ตรึงเวอร์ชันไว้ แก้ช่องโหว่ระดับ high/critical ที่มีเส้นทางเข้าถึงได้ก่อนเปิดบริการ อิมเมจ runtime ต้องใช้เพียง Next.js

```bash
docker build --target build -f docker/frontend.Dockerfile -t aphrodize-frontend:build --build-arg SITE_URL=https://aphrodize.duckdns.org .
docker run --rm --entrypoint pnpm aphrodize-frontend:build audit --prod
docker compose -f compose.vm.yml up -d
docker compose -f compose.vm.yml ps
docker compose -f compose.vm.yml exec -T api python -c "from urllib.request import urlopen; print(urlopen('http://127.0.0.1:8000/api/v1/health').status)"
```

ขั้นตอน build ตรวจ frontend lint, TypeScript และ production build หากการตรวจหรือ audit ล้มเหลว ให้แก้ก่อนเริ่มระบบ ห้ามข้ามการตรวจ VM ปัจจุบันมี RAM ประมาณ 4 GiB และไม่มี swap; หาก build ถูกยุติ ให้ build อิมเมจเดียวกันบนเครื่องที่มีหน่วยความจำมากกว่าแล้วโอนไป VM

## ตั้งให้ Windows เชื่อถือ HTTPS

Caddy ออกใบรับรองภายในสำหรับชื่อโฮสต์ที่ตั้งไว้ ส่งออกเฉพาะ CA สาธารณะ:

```bash
docker compose -f compose.vm.yml cp caddy:/data/caddy/pki/authorities/local/root.crt /home/aphrodize/aphrodize-local-ca.crt
sha256sum /home/aphrodize/aphrodize-local-ca.crt
```

ดาวน์โหลดจาก Windows PowerShell:

```powershell
scp aphrodize@172.30.81.237:~/aphrodize-local-ca.crt "$env:USERPROFILE\Downloads\aphrodize-local-ca.crt"
certutil -hashfile "$env:USERPROFILE\Downloads\aphrodize-local-ca.crt" SHA256
```

เปรียบเทียบ SHA-256 ของไฟล์จากทั้งสองเครื่อง ซึ่งต้องตรงกัน นำ root certificate สาธารณะเข้า Trusted Root Certification Authorities ของผู้ใช้ปัจจุบันด้วยตัวช่วยนำเข้าใบรับรองของ Windows เชื่อถือเฉพาะ CA ของ VM นี้ ห้ามส่งออกหรือโอน private key แล้วเปิด `https://aphrodize.duckdns.org`

ตรวจสมัครสมาชิก/เข้าสู่ระบบ ออกจากระบบ โปรไฟล์ และพฤติกรรม API ส่วนตัวจาก Windows การถ่ายภาพด้วยกล้องต้องใช้ HTTPS origin ที่เชื่อถือได้

## HTTPS ที่เชื่อถือได้สาธารณะบนเครือข่ายมหาวิทยาลัย

การตั้งค่า VM พื้นฐานใช้ CA ภายในของ Caddy หากต้องการเลี่ยงการติดตั้ง CA ในลูกข่ายทุกเครื่อง ให้ใช้ DuckDNS overlay เพื่อขอใบรับรอง Let's Encrypt ผ่านการตรวจ DNS-01 VM ยังคงใช้ private IP ได้ และไม่ได้ทำให้เข้าถึงจากนอกเครือข่ายมหาวิทยาลัย

เพิ่ม `DUCKDNS_API_TOKEN=<your account token>` ใน `.env` ส่วนตัว (สิทธิ์ 600) token อยู่ด้านบนของหน้า DuckDNS หลังเข้าสู่ระบบ ห้าม commit หรือวางในแชต คง A record ให้ชี้ private IP ของ VM อย่างชัดเจน
VM ต้องเข้าถึง DuckDNS และ Let's Encrypt ผ่าน HTTPS ขาออกได้ ทั้งโมดูล DuckDNS และการตรวจ ACME ใช้ resolver ของ Docker (`127.0.0.11:53`) ซึ่งส่งต่อไป DNS ที่โฮสต์ตั้งไว้ เครือข่ายมหาวิทยาลัยอาจบล็อกการ query public resolver โดยตรง

```bash
docker compose -f compose.vm.yml -f compose.duckdns.yml config --quiet
docker compose -f compose.vm.yml -f compose.duckdns.yml build caddy
docker compose -f compose.vm.yml -f compose.duckdns.yml up -d --no-deps caddy
curl --fail https://aphrodize.duckdns.org/login -o /dev/null
```

ใช้ไฟล์ Compose ทั้งสองสำหรับการอัปเดตครั้งต่อไป เพื่อให้ Caddy มี DNS provider และ token สำหรับต่ออายุอัตโนมัติ เก็บ `caddy_data` แบบถาวร ห้ามใช้ `down -v` หากใช้เพียง Compose พื้นฐานจะกลับไปใช้ CA ภายใน
ใบรับรองสาธารณะที่ออกแล้วจะเผยแพร่ชื่อโฮสต์ใน certificate transparency logs token ของ DuckDNS แก้ record ของชื่ออื่นในบัญชีเดียวกันได้ จึงควรใช้บัญชีเฉพาะเว็บไซต์นี้หากทำได้

## ข้อจำกัดก่อนเชื่อม GPU

ยังทำ image inference ไม่ได้ ห้ามอัปโหลดภาพส่วนตัวในระยะนี้ เพราะหากไม่มี worker งานที่เข้าคิวและการลบภาพต้นทางจะไม่เสร็จ การพยากรณ์ UV ต้องใช้ไฟล์โมเดล/ข้อมูล/snapshot ที่ไม่ได้รวมมาด้วย จึงยังไม่ควรคาดหวังว่าจะมีข้อมูล
การเชื่อม worker และ retention worker ฝั่ง VM ยังเป็นงานในอนาคต ฐานข้อมูล Redis และ MinIO ยังไม่เปิดพอร์ตบนโฮสต์ โดยจะเพิ่มเส้นทางเครือข่ายที่จำกัดการเข้าถึงภายหลัง

## เปิดการรีเฟรชพยากรณ์ UV ด้วยโมเดลเดิม

คัดลอกไดเรกทอรี `storage/models/uv`, `storage/data/uv` และ `storage/artifacts/uv` ทั้งหมดจากเครื่องฝึกโมเดลไปยัง path เดียวกันใต้ `~/Aphrodize` บน VM รักษา `active.json` และ bundle `versions/<version>` ที่อ้างถึงไว้ รวม `manifest.json`, `dataset.csv`, โมเดลทั้งสามเมือง และไฟล์ประเมินผล ห้ามคัดลอก `deployment.lock` ชั่วคราวจาก job ที่กำลังรัน หยุดโปรเซสเดิมที่เขียนข้อมูล UV ก่อนแทนที่ไฟล์เหล่านี้ registry ที่ active อยู่แล้วไม่ต้อง bootstrap หรือฝึกใหม่

profile เสริม `background` รัน `uv-refresh` ทันที จากนั้นทุกหกชั่วโมงเมื่อสำเร็จ หรือ retry หลัง 30 นาทีเมื่อล้มเหลว โดยดาวน์โหลดข้อมูล TEMIS และ Open-Meteo แล้วใช้พารามิเตอร์โมเดลเดิมโดยไม่ฝึกใหม่ API อ่าน snapshot ที่แชร์กันได้โดยไม่ต้อง restart

บน VM ให้ตั้งค่าเหล่านี้ใน `.env` ส่วนตัวตามผล `id -u` และ `id -g` ของบัญชีเจ้าของไฟล์ UV ที่อัปโหลด (ค่าเริ่มต้นทั้งคู่คือ 1000):

```dotenv
UV_REFRESH_UID=1000
UV_REFRESH_GID=1000
```

บัญชีนั้นต้องเขียนไดเรกทอรี UV ทั้งสามได้ โมเดลต้องมีสิทธิ์เขียนสำหรับ deployment lock แม้การรีเฟรชจะไม่แก้ bundle โมเดล หากคอนเทนเนอร์ก่อนหน้าสร้างไฟล์ที่ root เป็นเจ้าของ ให้แก้เจ้าของไดเรกทอรีเหล่านี้เป็นบัญชี deploy ก่อนเริ่มบริการ

รันจากรากโครงการบน VM หลังอัปโหลดไฟล์แล้ว:

```bash
cd ~/Aphrodize
docker compose -f compose.vm.yml --profile background config --quiet
docker compose -f compose.vm.yml --profile background run --rm --no-deps --build uv-refresh python /app/scripts/refresh_uv_forecast.py
docker compose -f compose.vm.yml --profile background up -d --no-deps uv-refresh
docker compose -f compose.vm.yml logs --tail 100 uv-refresh
```

เริ่ม job ตามรอบเมื่อการรีเฟรชครั้งเดียวสำเร็จแล้วเท่านั้น เมื่อรีเฟรชล้มเหลว log จะบอกสาเหตุ เช่น ไม่มีโมเดล ประวัติ TEMIS เปลี่ยน ข้อมูลสังเกตเก่า หรือไลบรารีโมเดลไม่เข้ากัน ห้ามฝึกใหม่อัตโนมัติเพื่อข้ามการตรวจเหล่านี้ API ปฏิเสธ snapshot ที่เก่ากว่าแปดชั่วโมง

บริการนี้ใช้อิมเมจ API ที่ build ในเครื่องและสคริปต์แบบอ่านอย่างเดียวจาก checkout บน VM หลังอัปเดต checkout หรือ dependency ให้ build และสร้าง `uv-refresh` ใหม่อย่างชัดเจนด้วย `up -d --no-deps --build uv-refresh`; deployment จาก registry ปัจจุบันอัปเดตเฉพาะ API/frontend
ใส่ Compose overlay เดิมทุกตัวในคำสั่งที่อัปเดตบริการเว็บด้วย เพื่อคงการตั้งค่า TLS

## การอัปเดตและข้อมูล

ตรวจและ commit ไฟล์ deployment อย่างเจาะจง หลีกเลี่ยง `git add .` สำหรับข้อมูลที่ยังไม่ตรวจ ดึงการอัปเดตที่อนุมัติแล้ว build ใหม่ จากนั้นรัน `up -d` ห้ามใช้ `down -v` เพราะลบข้อมูล
สำรอง PostgreSQL, MinIO, `.env` และ volume ของ Caddy CA อย่างปลอดภัย ต้องซ้อมสำรองและกู้คืนก่อนถือว่าเป็นบริการ production

## deploy release จาก registry ที่ผ่านการทดสอบ

ยังใช้ขั้นตอน build ในเครื่องข้างต้นได้ สำหรับการเผยแพร่อิมเมจและ deploy VM ด้วย GitHub Actions ใน repository เดียว ดู [การตั้งค่า CI/CD](cicd-vm.md) ขั้นตอนนี้รักษา Compose project และ TLS/worker overlay ที่ตั้งไว้ deploy API/frontend ด้วย image digest และเก็บสถานะ rollback ส่วนตัวบน VM
