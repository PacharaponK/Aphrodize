# CI และการป้องกัน main (ระยะที่ 1–2)

## CI

`.github/workflows/ci.yml` ทำงานเมื่อ push ไปที่ `dev`/`main`, เปิด PR ไปยังสองสาขานี้ หรือสั่งรันด้วยตนเอง ไม่มีตัวกรอง path ที่ข้ามการตรวจที่จำเป็น แต่ละ job มีเวลาจำกัด 20 นาที และการรันใหม่จะยกเลิกการรันเก่าของสาขาหรือ PR เดียวกัน
workflow ใช้ runner Ubuntu 24.04 ที่ GitHub จัดให้ สิทธิ์อ่าน repository เท่านั้น และ Actions ที่ตรึงเวอร์ชันด้วย commit โดยไม่ต้องใช้ความลับของ production หรือบริการที่ใช้งานจริง

ชื่อการตรวจที่บังคับต้องตรงตามนี้ทุกตัวอักษร (ค่าตั้งต้นผูกชื่อเหล่านี้กับ GitHub Actions app ID 15368 ที่ตรวจสอบแล้ว):

- `Backend CI`: Python 3.11 พร้อม dependency ของโครงการที่ล็อกเวอร์ชันและกลุ่ม `ci`; ตรวจ Ruff และชุด pytest ที่รากโครงการ รวม Headless OpenCV สำหรับการทดสอบ landmark
- `Frontend CI`: Node 24; pnpm 11.19.0 พร้อม pnpm lockfile ที่ commit ไว้; ตรวจ ESLint, `tests/*.mjs` ทั้งหมด (รวม fixture คำแนะนำข้ามชั้นระบบ), TypeScript และ production build

รันซ้ำในเครื่องจากราก repository:

```bash
uv sync --locked --no-default-groups --group ci --no-install-package opencv-python
uv run --no-sync ruff check backend tests scripts/release_manifest.py scripts/deploy_vm.py scripts/check-vm-readiness.py
uv run --no-sync python -m pytest
cd frontend
pnpm install --frozen-lockfile --ignore-scripts
pnpm lint
node --test tests/*.mjs
pnpm exec tsc --noEmit
pnpm build
```

ขั้นตอนนี้ตรวจโค้ดเว็บและ backend ส่วนการเชื่อม GPU/checkpoint และ deployment ของ production อยู่ในระยะอื่น dependency หลักและของ CI ถูก commit ใน `uv.lock`; job เหล่านี้จงใจไม่ติดตั้ง runtime ของ GPU ทั้งชุด
`label-studio-sdk` ดึง `opencv-python` มาด้วย CI จึงเว้นแพ็กเกจแบบ GUI และใช้ `opencv-python-headless` ที่ล็อกเวอร์ชันไว้ ซึ่งให้โมดูล `cv2` เดียวกัน เพื่อไม่ให้ wheel สองตัวเขียนทับกัน และไม่ให้การทดสอบพึ่งไลบรารีเดสก์ท็อป

## เปิดการป้องกัน main

JSON ที่ commit ไว้เป็นข้อเสนอการตั้งค่า ไม่ใช่หลักฐานว่าการป้องกันมีผลแล้ว ให้รัน CI หนึ่งครั้งก่อนเลือกการตรวจที่บังคับ ผู้ดูแลต้องนำการตั้งค่าไปใช้และอ่านกลับจาก GitHub; การ commit ไฟล์นี้ไม่ได้ตั้งค่าให้โดยอัตโนมัติ

เปิด https://github.com/PacharaponK/Aphrodize/settings/branches แล้วเพิ่มกฎป้องกันสาขาที่ตรงกับ `main` (หรือเพิ่มความเข้มงวดให้กฎเดิมที่ตรงกัน):

1. บังคับให้ใช้ pull request ก่อน merge การตั้งค่าเริ่มต้นไม่เพิ่มข้อบังคับให้ reviewer อนุมัติ เพื่อให้ผู้ดูแลคนเดียวใช้ PR ได้ แต่ต้องคงข้อกำหนดการอนุมัติเดิมที่เข้มงวดกว่าไว้
2. บังคับให้ `Backend CI` และ `Frontend CI` ผ่าน โดยเลือกแหล่งที่มาเป็น GitHub Actions และบังคับให้สาขาอัปเดตตาม main ก่อน merge
3. บังคับให้แก้ไขบทสนทนาใน PR ให้ครบก่อน merge
4. ไม่อนุญาตให้ข้ามการตั้งค่าข้างต้น รวมถึงผู้ดูแลระบบ
5. ปิดการ force push และการลบสาขาไว้

หากตั้งค่าผ่าน GitHub CLI ที่ยืนยันตัวตนแล้ว ให้ตรวจการป้องกันปัจจุบันก่อน:

```bash
gh api repos/PacharaponK/Aphrodize/branches/main/protection
```

หากยังไม่มีกฎ (404) สามารถนำค่าตั้งต้นที่เตรียมไว้ไปใช้จากราก repository:

```bash
gh api --method PUT repos/PacharaponK/Aphrodize/branches/main/protection \
  --input .github/main-protection.json
gh api repos/PacharaponK/Aphrodize/branches/main/protection
```

หากมีกฎอยู่แล้ว ให้รักษาการตั้งค่าที่เข้มงวดกว่า การตรวจที่บังคับ การผูกแหล่งที่มา และข้อจำกัดเดิม อย่าเขียนทับด้วยค่าตั้งต้นโดยไม่ตรวจสอบ ruleset ของ repository อาจป้องกัน main อยู่แล้ว จึงต้องตรวจด้วยก่อนเพิ่มกฎซ้ำ

## เกณฑ์ตรวจรับ

- การ push ไป dev และ PR ไป main ต้องสร้างการตรวจทั้งสองรายการและผ่าน
- การทดสอบที่จงใจให้ล้มเหลวบนสาขา PR ชั่วคราวต้องทำให้การตรวจล้มเหลวและบล็อก merge ให้คืนค่าหรือลบการทดสอบทดลองก่อน merge โดยไม่เพิ่มช่องทางข้ามข้อบังคับ
- PR ต้องอัปเดตตาม main และแก้ไขบทสนทนาให้ครบ
- ตรวจว่าหน้าการป้องกันหรือ API แสดงการตั้งค่าที่จำเป็นจริง จึงรายงานว่าระยะที่ 2 เสร็จสมบูรณ์ได้

แหล่งอ้างอิง: [uv ใน GitHub Actions](https://docs.astral.sh/uv/guides/integration/github/),
[API การป้องกันสาขาของ GitHub](https://docs.github.com/en/rest/branches/branch-protection).
