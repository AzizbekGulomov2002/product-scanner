# Excel + ZIP import — qo'llanma

Mahsulotlarni admin panel orqali ommaviy yuklash uchun **Excel (yoki CSV)** va ixtiyoriy **ZIP** fayl tayyorlang.

**Admin:** http://localhost:8000/admin/ → **Bulk Import** yoki **Import**

---

## 1. Excel / CSV formati

### Majburiy ustunlar

| Ustun | Tavsif | Misol |
|-------|--------|-------|
| `external_id` | Mahsulot ID (noyob) | `001` |
| `name` | Mahsulot nomi | `Skovorodka` |

### Ixtiyoriy ustunlar

| Ustun | Tavsif | Misol |
|-------|--------|-------|
| `barcode` | Shtrix-kod | `4012345678901` |
| `image_files` | ZIP ichidagi fayl nomlari (vergul bilan) | `001_front.jpg,001_back.jpg` |

> Ustun nomlari katta/kichik harf farq qilmaydi — tizim avtomatik `external_id`, `name` qilib o'qiydi.

### Namuna fayllar

| Fayl | Maqsad |
|------|--------|
| `products_template.csv` | Oddiy CSV shablon |
| `products_template.xlsx` | Excel shablon |
| `products_flat_example.csv` | Fayl nomlari bilan (2-usul) |

---

## 2. ZIP — rasmlarni joylash (2 ta usul)

### Usul A — Papka bo'yicha (TAVSIYA)

Har bir mahsulot uchun **ID nomli papka** oching. Papka ichiga shu mahsulot rasmlarini qo'ying.

```
product_images_folder_example.zip
├── 001/
│   ├── SkovorodkaA-1.jpg
│   └── SkovorodkaA-2.jpg
├── 002/
│   ├── sopol.jpg
│   └── sopol2.jpg
└── 006/
    ├── airpods-pro-3a.jpeg
    ├── airpods-pro-c.jpg
    └── airpods-pro-3c.webp
```

**Qoidalar:**
- Papka nomi = Excel dagi `external_id` (masalan `001`, `006`)
- Bir papkada bir nechta rasm bo'lishi mumkin
- Birinchi rasm **asosiy (primary)** deb belgilanadi
- Qo'llab-quvvatlanadigan formatlar: `.jpg`, `.jpeg`, `.png`, `.webp`
- Excel da `image_files` ustuni **bo'sh** qoldirilishi mumkin

**Misol ZIP:** `product_images_folder_example.zip`

---

### Usul B — Tekis (flat) ZIP + image_files ustuni

Barcha rasmlar ZIP ning **ildizida** (papkasiz) turadi. Excel da qaysi fayl qaysi mahsulotga tegishli ekanini `image_files` ustunida yozasiz.

**Excel (`products_flat_example.csv`):**

```csv
external_id,name,barcode,image_files
001,Skovorodka,,001_front.jpg,001_back.jpg
006,Airpods pro 3,,006_1.jpeg,006_2.jpg,006_3.webp
```

**ZIP (`product_images_flat_example.zip`):**

```
product_images_flat_example.zip
├── 001_front.jpg
├── 001_back.jpg
├── 006_1.jpeg
├── 006_2.jpg
└── 006_3.webp
```

> `image_files` da fayl nomlari **vergul bilan** ajratiladi. Fayl nomi ZIP ichidagi nom bilan **to'liq mos** bo'lishi kerak.

---

## 3. Import qilish (admin)

1. Django server ishlab turgan bo'lsin: `make server`
2. Celery worker ishlab turgan bo'lsin (embedding uchun): `make worker`
3. Admin: http://localhost:8000/admin/
4. **Bulk Import** → Excel/CSV va ZIP yuklang
5. **Mode** tanlang:
   - **Create or Update** — yangi qo'shadi, mavjud ID ni yangilaydi
   - **Create Only** — faqat yangi mahsulot
   - **Update Only** — faqat mavjud mahsulotni yangilaydi
6. **Start Import** bosing
7. Import tugagach embedding avtomatik navbatga qo'yiladi

---

## 4. Tez-tez uchraydigan xatolar

| Xato | Sabab | Yechim |
|------|-------|--------|
| Missing required columns | `external_id` yoki `name` yo'q | Ustun nomlarini tekshiring |
| Image not found in ZIP | Fayl nomi mos kelmadi | `image_files` va ZIP nomlarini solishtiring |
| Product already exists | Create Only rejimida ID bor | Create or Update ishlating |
| Product not found | Update Only, ID bazada yo'q | Avval mahsulot qo'shing |

---

## 5. Tayyor shablonlar (shu papkada)

```
sample_data/
├── products_template.csv          # CSV shablon (papka usuli)
├── products_template.xlsx         # Excel shablon
├── products_flat_example.csv      # Flat usul uchun CSV
├── product_images_folder_example.zip   # Papka usuli ZIP
├── product_images_flat_example.zip     # Flat usul ZIP
└── IMPORT_GUIDE.md                # Bu qo'llanma
```

Shablonlarni o'zgartirib, o'z mahsulotlaringizni qo'shing va admin orqali import qiling.
