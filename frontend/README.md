# Client

พื้นที่สำหรับ web client ของ Aphrodize

- `design/` — wireframe และ design guidance ก่อนเริ่ม implementation
- `index.html` — responsive, static front-end prototype
- `login.html` — static login page พร้อม client-side validation (ไม่เชื่อม authentication จริง)
- `styles.css` และ `app.js` — styles และ interactions สำหรับ prototype

เปิด `client/index.html` ใน browser ได้ทันที โดยไม่ต้อง install dependency.

สำหรับส่งให้เพื่อนดู ให้เปิด `showcase.html` เพื่อเลือกทุกหน้าใน static prototype: login, dashboard, capture, quality-rejected, result detail, trend และ recommendation.

`theme.css` กำหนด pastel glass theme (ฟ้า–ลาเวนเดอร์–ชมพูอ่อน) สำหรับ visual style ของ client.

`mobile-menu.css` รองรับ hamburger drawer และการวาง theme toggle บน topbar.
