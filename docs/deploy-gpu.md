# GPU worker บน Windows ผ่าน SSH tunnel

การทดสอบ GPU บน Windows ผ่านด้วย GTX 1660 SUPER, VRAM 6 GiB และ PyTorch 2.1.2 การตั้งค่านี้คง PyTorch 2.1.2 / CUDA 11.8 และใช้ Python 3.11 ซึ่งจำเป็นสำหรับการ import `datetime.UTC` ของ worker อิมเมจ PyTorch ที่ดาวน์โหลดมายังคงใช้เป็นหลักฐานว่าทดสอบฮาร์ดแวร์สำเร็จ ส่วนอิมเมจ worker มี dependency ของโครงการรวมอยู่ด้วย
ยังไม่ได้ build หรือรันการตั้งค่านี้กับ checkpoint ของเจ้าของโครงการ

## สิ่งที่ต้องเตรียมบน VM

build และตรวจสอบบริการ VM ตาม `docs/deploy-vm.md` ก่อน สำหรับการเข้าถึงของ worker ต้องระบุไฟล์ VM ทั้งสองในคำสั่ง Compose หลังจากนี้เสมอ:

```bash
cd ~/Aphrodize
docker compose -f compose.vm.yml -f compose.vm-worker-access.yml config --quiet
docker compose -f compose.vm.yml -f compose.vm-worker-access.yml up -d
```

พอร์ต PostgreSQL, Redis และ MinIO ผูกกับ loopback ของ VM เท่านั้น ไม่เปิดสู่ LAN การรับส่งข้อมูลของ worker ใช้ SSH ที่เชื่อถือได้ ให้ปิด GPU worker ไว้จนกว่าจะเริ่ม VM, ตรวจ frontend, ตรวจ dependency และเตรียมฐานข้อมูล/ที่เก็บข้อมูลเสร็จ
worker ใช้ข้อมูลรับรองฐานข้อมูล/Redis/MinIO ที่ตรงกัน ไม่ใช้ความลับของ API หรือ JWT ข้อมูลรับรองบริการในต้นแบบนี้ยังเข้าถึงข้อมูลได้กว้าง จึงใช้ได้เฉพาะเครื่อง worker ที่เชื่อถือได้ การสร้าง role เฉพาะที่จำกัดสิทธิ์เป็นงานเสริมความปลอดภัยในอนาคต

## โอนชุดติดตั้งที่เตรียมไว้

จาก Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force C:\Users\student\ai-eco\aphrodize-gpu-runtime
cd C:\Users\student\ai-eco\aphrodize-gpu-runtime
scp aphrodize@172.30.81.237:~/aphrodize-gpu-setup.tar.gz .
tar -xzf .\aphrodize-gpu-setup.tar.gz
scp aphrodize@172.30.81.237:~/Aphrodize/.env.gpu .
```

โฟลเดอร์ runtime แยกนี้ช่วยไม่ให้เขียนทับโครงการ Windows เดิม ไฟล์ซอร์สมาจาก snapshot ของ VM เดียวกัน ส่วนโมเดลอยู่ในไดเรกทอรีโครงการเดิม
ถือว่า `.env.gpu` เป็นความลับ: ห้ามพิมพ์ วางข้อความ commit หรือแชร์ และจำกัดการเข้าถึงในเครื่องไว้เฉพาะผู้ใช้ Windows ของคุณ ไฟล์ซอร์สที่บีบอัดไม่มีข้อมูลรับรองหรือโมเดล

## เปิด SSH tunnel ค้างไว้

เปิดหน้าต่าง PowerShell แยก:

```powershell
ssh -N -T -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -L 127.0.0.1:15432:127.0.0.1:5432 -L 127.0.0.1:16379:127.0.0.1:6379 -L 127.0.0.1:19000:127.0.0.1:9000 aphrodize@172.30.81.237
```

ยืนยันตัวตนในหน้าต่างนั้นและเปิดค้างไว้; Ctrl+C จะปิด tunnel การไม่มีข้อความหลังยืนยันตัวตนเป็นเรื่องปกติ คอนเทนเนอร์เข้าถึงผ่าน `host.docker.internal`
ตรวจว่าเข้าถึงพอร์ต forward บน Windows loopback ได้ก่อนเริ่ม worker หากการตรวจล้มเหลว อย่าเปลี่ยนการ bind เป็น `0.0.0.0`; ให้ตรวจการกำหนดเส้นทางของ Docker Desktop

## build worker แล้วตรวจการเชื่อมต่อจากคอนเทนเนอร์

ในโฟลเดอร์ runtime:

```powershell
docker compose --env-file .env.gpu -f compose.gpu.yml config --quiet
docker compose --env-file .env.gpu -f compose.gpu.yml build
docker compose --env-file .env.gpu -f compose.gpu.yml run --rm --no-deps --entrypoint python inference-worker -c "import socket; [socket.create_connection(('host.docker.internal',p),5).close() for p in (15432,16379,19000)]; print('TCP connectivity OK')"
```

ขั้นตอนนี้ตรวจเพียงการเข้าถึง TCP จากนั้นให้ตรวจข้อมูลรับรองและวงจรเขียน/อ่าน/ลบออบเจ็กต์จำลอง การวินิจฉัยนี้ไม่สร้างงาน inference และไม่ใช้ภาพส่วนตัว:

```powershell
$probe = @'
import asyncio
from uuid import uuid4
from sqlalchemy import text
from backend.core.db.session import SessionLocal, close_database
from backend.libs.redis_client import get_arq_pool
from backend.libs.minio_client import put_bytes, get_bytes, remove_objects

async def main():
    stage = "Redis"
    try:
        redis = await get_arq_pool()
        try:
            assert await redis.ping()
            print("Redis authentication: OK")
        finally:
            await redis.aclose()
        stage = "PostgreSQL"
        try:
            async with SessionLocal() as session:
                assert await session.scalar(text("SELECT 1")) == 1
            print("PostgreSQL authentication: OK")
        finally:
            await close_database()
        stage = "MinIO"
        key = "diagnostics/" + str(uuid4()) + ".txt"
        payload = b"aphrodize-connectivity-test"
        try:
            await asyncio.to_thread(put_bytes, key, payload, "text/plain")
            assert await asyncio.to_thread(get_bytes, key) == payload
        finally:
            await asyncio.to_thread(remove_objects, [key])
        print("MinIO write/read/delete: OK")
    except Exception as error:
        print(stage + " probe failed: " + type(error).__name__)
        raise SystemExit(1) from None

asyncio.run(main())
'@
$probe | docker compose --env-file .env.gpu -f compose.gpu.yml run --rm -T --no-deps --entrypoint python inference-worker -
```

ห้ามพิมพ์ข้อความ exception ดิบหรือข้อมูลรับรอง แก้การตรวจที่ล้มเหลวก่อนเริ่มงานจริง ต้องลบออบเจ็กต์วินิจฉัยแม้การอ่านจะล้มเหลว

## ตรวจการ mount โมเดลเริ่มต้นและ CUDA

```powershell
docker compose --env-file .env.gpu -f compose.gpu.yml run --rm --no-deps --entrypoint python inference-worker -c "import torch; from ai.ffhq_wrinkle.modeling import load_wrinkle_model; assert torch.cuda.is_available(); torch.cuda.reset_peak_memory_stats(); b=load_wrinkle_model('UNet',requested_device='cuda'); torch.cuda.synchronize(); print('Model device:',b.device); print('Checkpoint SHA256:',b.checkpoint_sha256); print('Load peak allocated MiB:',torch.cuda.max_memory_allocated()/1024**2)"
```

ตัวโหลดตรวจ SHA-256 และสถาปัตยกรรมของ checkpoint ก่อนโหลด ค่าแฮชที่คาดหวังของ UNet checkpoint ทางการคือ
`883034b3e0726dcdae946c312106dfde1d354ea5455fa21cba045a73058f4a25`.
ผลหน่วยความจำตอนโหลดไม่ใช่หน่วยความจำสูงสุดของ pipeline ทั้งหมด ก่อนถือว่า GPU deployment พร้อมใช้งาน ต้องทดสอบภาพจริงที่ได้รับความยินยอม ครอบคลุม preprocessing, face parsing, MediaPipe, inference, การบันทึกผล และการลบ worker แบบ UNet เริ่มต้นนี้ไม่ได้เลือกใช้ archive ZIP หรือ SwinUNETR checkpoint

## เริ่มเมื่อการตรวจทั้งหมดผ่านแล้วเท่านั้น

```powershell
docker compose --env-file .env.gpu -f compose.gpu.yml up -d --no-deps inference-worker
docker compose --env-file .env.gpu -f compose.gpu.yml logs --tail 50 inference-worker
```

worker ยังคงทำงานพร้อมกันครั้งละหนึ่ง job ตรวจสถานะ queued -> running -> completed จากเว็บ การทำงานของ GPU และการลบภาพต้นฉบับ รวมถึงพฤติกรรมเมื่อปฏิเสธภาพคุณภาพต่ำหรือ worker หลุดการเชื่อมต่อ
อย่าถือว่าการ restart จะกู้ทุก job ที่กำลังรันได้ ต้องทดสอบการกู้คืนและการเก็บรักษาแยกต่างหาก worker ยังรับผิดชอบล้างผลลัพธ์เมื่อครบ 24 ชั่วโมง จึงต้องเปิด worker และ tunnel ค้างไว้ ยังต้องมี retention worker ฝั่ง VM ก่อนใช้งาน production แบบไม่มีผู้ดูแล
