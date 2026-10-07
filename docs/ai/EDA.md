# การสำรวจข้อมูล FFHQ-Wrinkle (EDA)

รัน EDA ก่อนฝึกเพื่อตรวจว่า mask ริ้วรอยที่ทำด้วยมือทุกภาพจับคู่กับภาพ FFHQ ต้นทางได้ และวัดความไม่สมดุลของ label ขั้นตอนนี้ไม่แก้ dataset

## รันบน Windows

```cmd
cd C:\Users\student\Aphrodize
py -m pip install -r requirements-eda.txt
py scripts\eda_ffhq_wrinkle.py --data-root C:\Users\student\ffhq-wrinkle-dataset\data
```

## ผลลัพธ์

- `summary.json` — จำนวน การตรวจขนาดภาพ/mask และสถิติอัตราส่วนพื้นที่
- `manual_mask_metrics.csv` — หนึ่งแถวต่อคู่ที่จับคู่ได้
- `missing_images.csv` — mask ที่ไม่มีภาพ FFHQ คู่กัน
- `wrinkle_area_histogram.png` — การกระจายความหนาแน่นของ label
- `sample_pairs.png` — ตัวอย่างใบหน้า mask และ overlay

ใช้ Dice และ IoU แทนการดู pixel accuracy อย่างเดียว เพราะพิกเซลริ้วรอยมีสัดส่วนน้อย
