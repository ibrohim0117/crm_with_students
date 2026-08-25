# CRM + Savdo tizimi — To'liq loyiha rejasi va tasklar

> **Backend:** Django REST Framework (o'quvchilar qo'lda yozadi)
> **Frontend / Mobile:** API tayyor bo'lgach AI orqali generatsiya qilinadi
> **Hujjat sanasi:** 2026-08-22
> **Muallif:** Ibrohim To'lqinov (mentor)

---

## 0. Loyiha haqida qisqacha

Kichik CRM + onlayn savdo tizimi. Ikki rol bor:

| Rol | Kim | Qanday olinadi |
|---|---|---|
| `user` | Oddiy xaridor | Ro'yxatdan o'tganda avtomatik beriladi |
| `admin` | Boshqaruvchi | Django admin panelidan **qo'lda** belgilanadi |

**User qiladi:** katalogni ko'radi, like bosadi, comment yozadi, savatchaga qo'shadi, zakaz qiladi, buyurtmani kuzatadi, qaytarish so'rovi yuboradi.

**Admin qiladi:** kategoriya/mahsulot/ombor CRUD, buyurtma statusini boshqaradi, to'liq statistikani ko'radi.

**Auth o'ziga xosligi:** SMS emas, **Telegram bot** orqali tasdiqlash kodi yuboriladi.

---

## 1. Texnologiyalar stack

| Qatlam | Tanlov | Izoh |
|---|---|---|
| Til | Python 3.12 | |
| Framework | Django 5.x + DRF 3.15 | |
| DB | PostgreSQL 16 | SQLite bilan boshlanmasin — ORM farqlari chiqadi |
| Auth | `djangorestframework-simplejwt` | access 30 daq, refresh 7 kun |
| Bot | `aiogram 3` (alohida process) | webhook emas, polling — o'quvchilarga oson |
| Queue | Celery + Redis | kod yuborish, hisobot, cache tozalash |
| Cache | Redis | statistika endpointlari uchun |
| Filter | `django-filter` | |
| Docs | `drf-spectacular` (Swagger + Redoc) | frontendni AI yozishi uchun **majburiy** |
| Media | local (dev) → S3/MinIO (prod) | |
| Konteyner | Docker + docker-compose | |
| CI | GitHub Actions (lint + test) | |
| Lint | ruff + black + isort | pre-commit |
| Test | pytest + pytest-django + factory-boy | |

---

## 2. Loyiha strukturasi

```
crm_project/
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── local.py
│   │   └── prod.py
│   ├── urls.py
│   ├── celery.py
│   └── wsgi.py / asgi.py
├── apps/
│   ├── common/        # BaseModel, pagination, permissions, exception handler, utils
│   ├── users/         # User, VerificationCode, auth API
│   ├── catalog/       # Category, SubCategory, Unit, Product, ProductImage
│   ├── interactions/  # Like, Comment
│   ├── orders/        # Cart, CartItem, Order, OrderItem, Return
│   ├── inventory/     # StockMovement, Supply
│   └── analytics/     # statistika API (model yo'q, faqat query)
├── bot/               # aiogram bot (alohida entrypoint)
├── tests/
├── docker/
├── .env.example
├── requirements/
│   ├── base.txt
│   ├── local.txt
│   └── prod.txt
└── README.md
```

**Qoida:** har bir app ichida `models.py`, `serializers.py`, `views.py`, `urls.py`, `filters.py`, `permissions.py`, `services.py`, `admin.py`. Biznes-logika **`services.py`** da, view'da emas.

---

## 3. Ma'lumotlar modeli

### 3.1 `common.BaseModel` (abstract)

```
created_at   DateTimeField(auto_now_add=True)
updated_at   DateTimeField(auto_now=True)
```

Barcha modellar shundan meros oladi.

### 3.2 `users.User` (AbstractBaseUser + PermissionsMixin)

| Maydon | Tur | Izoh |
|---|---|---|
| `full_name` | CharField(150) | majburiy |
| `phone_number` | CharField(13), **unique** | `+998901234567` formatida normalize qilinadi, `USERNAME_FIELD` |
| `email` | EmailField, unique | majburiy |
| `password` | hash | |
| `bio` | TextField(blank=True) | optional |
| `avatar` | ImageField(blank=True, null=True) | optional |
| `role` | CharField(choices: `user`/`admin`, default=`user`) | |
| `is_active` | Boolean, **default=False** | kod tasdiqlangandan keyin `True` |
| `is_staff` | Boolean, default=False | Django admin panel uchun |
| `telegram_id` | BigIntegerField(null=True, blank=True) | botga /start bosganda yoziladi |
| `last_login_at` | DateTimeField(null=True) | "faol userlar" statistikasi uchun |

> **Muhim:** `role='admin'` qilinganda `is_staff=True` ham bo'lishi kerak. Buni `save()` yoki `post_save` signal orqali avtomatlashtiring.

### 3.3 `users.VerificationCode`

| Maydon | Tur |
|---|---|
| `user` | FK(User, related_name='codes') |
| `code` | CharField(6) |
| `purpose` | choices: `register`, `reset_password` |
| `is_used` | Boolean, default=False |
| `attempts` | PositiveSmallInteger, default=0 |
| `expires_at` | DateTimeField |
| `created_at` | DateTimeField |

**Indeks:** `(user, purpose, is_used)`.

### 3.4 `catalog.Category`
`name` (unique), `slug` (unique), `image`, `is_active`

### 3.5 `catalog.SubCategory`
`category` FK, `name`, `slug`, `is_active` — `unique_together (category, slug)`

### 3.6 `catalog.Unit`
`name` ("Kilogramm"), `short_name` ("kg")
Boshlang'ich data: kg, litr, dona, metr, quti, gramm, paket.

### 3.7 `catalog.Product`

| Maydon | Tur | Izoh |
|---|---|---|
| `subcategory` | FK(SubCategory, related_name='products') | |
| `name` | CharField(255) | |
| `slug` | SlugField, unique | |
| `description` | TextField(blank=True) | |
| `price` | Decimal(12,2) | sotuv narxi |
| `discount_price` | Decimal(12,2), null | ixtiyoriy |
| `cost_price` | Decimal(12,2), null | tannarx — foyda hisoblash uchun |
| `unit` | FK(Unit) | |
| `quantity` | Decimal(12,3), default=0 | ombordagi qoldiq |
| `min_quantity` | Decimal(12,3), default=0 | "yana kerak" chegarasi |
| `sku` | CharField(50), unique, null | |
| `views_count` | PositiveInteger, default=0 | "eng ko'p so'ralgan" |
| `is_active` | Boolean, default=True | |
| `created_by` | FK(User, null) | |

**Indekslar:** `(is_active, subcategory)`, `slug`, `name` (search uchun `GinIndex` bonus).

### 3.8 `catalog.ProductImage`
`product` FK(related_name='images'), `image`, `is_main` (Boolean)
Qoida: bitta mahsulotda faqat bitta `is_main=True`.

### 3.9 `interactions.Like`
`user` FK, `product` FK — **`unique_together (user, product)`**

### 3.10 `interactions.Comment`
`user` FK, `product` FK(related_name='comments'), `text`, `parent` FK(self, null — javob uchun), `is_active` (default=True)

### 3.11 `orders.Cart`
`user` OneToOne(User)

### 3.12 `orders.CartItem`
`cart` FK(related_name='items'), `product` FK, `quantity` Decimal(12,3)
**`unique_together (cart, product)`**

### 3.13 `orders.Order`

| Maydon | Tur |
|---|---|
| `user` | FK(User, related_name='orders') |
| `order_number` | CharField(20), unique — `ORD-20260822-0001` |
| `status` | choices: `new`, `confirmed`, `shipping`, `delivered`, `cancelled`, `returned` |
| `total_price` | Decimal(14,2) — **snapshot** |
| `address` | CharField(255) |
| `contact_phone` | CharField(13) |
| `note` | TextField(blank=True) |

### 3.14 `orders.OrderItem`
`order` FK(related_name='items'), `product` FK(on_delete=PROTECT), `quantity`, `price` (**buyurtma paytidagi narx snapshot**), `total`

> ⚠️ Narxni `product.price` dan **o'qib ko'rsatmang** — mahsulot narxi keyin o'zgarsa eski buyurtma buziladi.

### 3.15 `orders.OrderStatusHistory`
`order` FK, `from_status`, `to_status`, `changed_by` FK(User), `comment`

### 3.16 `orders.Return` (qaytarish)
`order_item` FK, `quantity`, `reason`, `status` (`pending`/`approved`/`rejected`), `processed_by`

### 3.17 `inventory.StockMovement`

| Maydon | Tur | Izoh |
|---|---|---|
| `product` | FK(related_name='movements') | |
| `type` | choices: `in`, `out`, `return`, `write_off` | |
| `quantity` | Decimal(12,3) | doim musbat |
| `price` | Decimal(12,2), null | kirim narxi |
| `order` | FK(Order, null) | `out`/`return` uchun |
| `comment` | CharField(255) | |
| `created_by` | FK(User, null) | |

**Qoida:** `Product.quantity` faqat `StockMovement` orqali o'zgaradi (service funksiyada, `transaction.atomic` ichida). Qo'lda `product.quantity = X` yozish **taqiqlanadi**.

---

## 4. AUTH oqimi (batafsil)

```
1. POST /auth/register/
   {full_name, phone_number, email, password, bio?, avatar?}
   → User yaratiladi: is_active=False
   → Javob: "Botga /start bosing va raqamingizni yuboring"  (bot link qaytariladi)

2. User Telegram botga kiradi → /start → "📱 Raqamni yuborish" tugmasi
   → bot contact.phone_number ni oladi → normalize qiladi
   → shu raqamli User bor va is_active=False bo'lsa:
        - user.telegram_id saqlanadi
        - 6 xonali random kod (100000–999999) yaratiladi
        - expires_at = now + 5 daqiqa
        - kod botga yuboriladi
   → User topilmasa: "Avval saytda ro'yxatdan o'ting"

3. POST /auth/confirm/   {phone_number, code}
   → kod bor / is_used=False / expires_at > now / attempts < 5
   → OK: user.is_active=True, code.is_used=True, JWT qaytariladi
   → Xato: attempts += 1

4. POST /auth/resend-code/  {phone_number}
   → Agar oxirgi kod HALI YAROQLI va ishlatilmagan bo'lsa → 400:
     "Avvalgi kod hali amal qiladi, {N} soniyadan keyin urinib ko'ring"
   → Aks holda eski kodlarni is_used=True qilib, yangi kod yuboriladi

5. POST /auth/login/  {phone_number, password}
   → user yo'q          → 404 "Bunday foydalanuvchi topilmadi"
   → parol xato         → 400 "Telefon raqam yoki parol xato"
   → is_active=False    → 403 "Akkaunt tasdiqlanmagan"
   → OK                 → {access, refresh, user}

6. Reset password:
   POST /auth/password/reset/          {phone_number}  → botga kod
   POST /auth/password/reset/confirm/  {phone_number, code, new_password, confirm_password}
   → parol yangilanadi, barcha refresh tokenlar blacklist qilinadi
```

**Xavfsizlik qoidalari:**
- Kod `attempts >= 5` bo'lsa bloklanadi, yangi kod so'rash kerak.
- `resend-code` throttle: 1 daqiqada 1 marta, kuniga 5 marta (`ScopedRateThrottle`).
- Kod tekshirishda `constant time` shart emas, lekin **kodni javobda qaytarmang** (hatto DEBUG'da ham).
- Telefon raqam har doim bitta formatga keltiriladi: `+998XXXXXXXXX`.

---

## 5. API endpointlar (to'liq ro'yxat)

Base: `/api/v1/`

### 5.1 Auth — `/auth/`
| Method | URL | Ruxsat | Tavsif |
|---|---|---|---|
| POST | `/auth/register/` | AllowAny | ro'yxatdan o'tish |
| POST | `/auth/confirm/` | AllowAny | kodni tasdiqlash |
| POST | `/auth/resend-code/` | AllowAny | kodni qayta yuborish |
| POST | `/auth/login/` | AllowAny | JWT olish |
| POST | `/auth/token/refresh/` | AllowAny | access yangilash |
| POST | `/auth/logout/` | IsAuthenticated | refresh blacklist |
| POST | `/auth/password/reset/` | AllowAny | kod so'rash |
| POST | `/auth/password/reset/confirm/` | AllowAny | parolni tiklash |
| POST | `/auth/password/change/` | IsAuthenticated | eski parol bilan almashtirish |
| GET | `/auth/me/` | IsAuthenticated | profil |
| PATCH | `/auth/me/` | IsAuthenticated | profilni yangilash (avatar, bio, full_name, email) |

### 5.2 Katalog — public read
| Method | URL | Ruxsat |
|---|---|---|
| GET | `/categories/` | AllowAny |
| GET | `/categories/{slug}/` | AllowAny |
| GET | `/subcategories/?category={slug}` | AllowAny |
| GET | `/products/` | AllowAny |
| GET | `/products/{slug}/` | AllowAny (+ `views_count` +1) |
| GET | `/units/` | AllowAny |

**`/products/` query paramlar:**
`?search=` (name, description) · `?category=` · `?subcategory=` · `?min_price=` · `?max_price=` · `?in_stock=true` · `?ordering=price,-price,-created_at,-views_count,-likes_count` · `?page=&page_size=`

### 5.3 Interaksiya
| Method | URL | Ruxsat |
|---|---|---|
| POST | `/products/{id}/like/` | IsAuthenticated (toggle: qo'shadi/o'chiradi) |
| GET | `/products/{id}/comments/` | AllowAny |
| POST | `/products/{id}/comments/` | IsAuthenticated |
| PATCH/DELETE | `/comments/{id}/` | IsOwnerOrAdmin |
| GET | `/me/likes/` | IsAuthenticated |

### 5.4 Savatcha
| Method | URL |
|---|---|
| GET | `/cart/` — itemlar + umumiy summa |
| POST | `/cart/items/` — `{product_id, quantity}` |
| PATCH | `/cart/items/{id}/` — `{quantity}` |
| DELETE | `/cart/items/{id}/` |
| DELETE | `/cart/clear/` |

Barchasi `IsAuthenticated`.

### 5.5 Buyurtma
| Method | URL | Tavsif |
|---|---|---|
| POST | `/orders/` | savatchadan buyurtma yaratish `{address, contact_phone, note}` |
| GET | `/orders/` | mening buyurtmalarim |
| GET | `/orders/{id}/` | detail |
| POST | `/orders/{id}/cancel/` | faqat `new`/`confirmed` holatida |
| POST | `/orders/{id}/return/` | `{items: [{order_item_id, quantity, reason}]}` |

### 5.6 Admin — `/admin-api/` (`IsAdminRole`)
| Method | URL |
|---|---|
| CRUD | `/admin-api/categories/` |
| CRUD | `/admin-api/subcategories/` |
| CRUD | `/admin-api/units/` |
| CRUD | `/admin-api/products/` |
| POST/DELETE | `/admin-api/products/{id}/images/` |
| GET/PATCH | `/admin-api/orders/` — status o'zgartirish |
| GET | `/admin-api/users/` — filter: `?is_active=&role=&search=` |
| POST | `/admin-api/users/{id}/block/` , `/unblock/` |
| GET/POST | `/admin-api/stock/movements/` — kirim/chiqim |
| GET | `/admin-api/returns/` , PATCH `/admin-api/returns/{id}/` |

### 5.7 Statistika — `/admin-api/stats/`

| URL | Nima qaytaradi |
|---|---|
| `/stats/overview/?period=day\|week\|month` | jami savdo summasi, buyurtmalar soni, yangi userlar, o'rtacha chek, foyda (`price − cost_price`) |
| `/stats/sales/?from=&to=&group_by=day\|week\|month` | grafik uchun massiv: `[{date, orders, revenue, profit}]` |
| `/stats/products/top-selling/?limit=10&period=` | eng ko'p sotilgan (miqdor va summa bo'yicha) |
| `/stats/products/least-selling/?limit=10` | eng kam sotilgan |
| `/stats/products/most-viewed/?limit=10` | eng ko'p so'ralgan (`views_count`) |
| `/stats/products/most-liked/?limit=10` | eng ko'p like olgan |
| `/stats/products/most-returned/?limit=10` | eng ko'p qaytib kelgan |
| `/stats/inventory/` | bazada qancha qoldi: jami qoldiq, jami qoldiq qiymati |
| `/stats/inventory/low-stock/` | `quantity <= min_quantity` — "yana kerak" ro'yxati |
| `/stats/inventory/out-of-stock/` | `quantity = 0` |
| `/stats/users/active/?period=` | faol userlar soni (`last_login_at` yoki buyurtma qilganlar) |
| `/stats/users/top-customers/?limit=10` | eng ko'p xarid qilgan mijozlar |
| `/stats/orders/by-status/` | har bir status bo'yicha soni |

**Barcha statistika ORM aggregate bilan yoziladi** — Python `for` loop bilan hisoblash **taqiqlanadi**:
`Sum`, `Count`, `Avg`, `F`, `Q`, `Case/When`, `TruncDate/TruncWeek/TruncMonth`, `annotate`, `values`.

Cache: `overview` va `sales` → Redis, TTL 5 daqiqa.

---

## 6. Umumiy standartlar

### 6.1 Javob formati

Muvaffaqiyat (list):
```json
{
  "count": 120,
  "next": "http://.../products/?page=3",
  "previous": "http://.../products/?page=1",
  "results": [ ... ]
}
```

Xatolik (custom exception handler orqali **hammasi bir xil**):
```json
{
  "success": false,
  "message": "Validatsiya xatosi",
  "errors": { "phone_number": ["Bu raqam allaqachon ro'yxatdan o'tgan"] }
}
```

### 6.2 Status kodlar
`200` OK · `201` yaratildi · `204` o'chirildi · `400` validatsiya · `401` token yo'q/eskirgan · `403` ruxsat yo'q · `404` topilmadi · `429` throttle · `500` server

### 6.3 Pagination
`PageNumberPagination`, `page_size=20`, `max_page_size=100`.

### 6.4 Permission klasslari (`common/permissions.py`)
`IsAdminRole`, `IsOwnerOrReadOnly`, `IsOwnerOrAdmin`, `IsActiveUser`

---

## 7. Sprintlar va tasklar

Har bir task: **ID · nom · kim · taxminiy soat · Definition of Done**

---

### 🟦 Sprint 0 — Fundament (2 kun)

| ID | Task | Soat | DoD |
|---|---|---|---|
| `S0-01` | Repo, `.gitignore`, branch strategiya, README skeleti | 1 | `main`, `develop` branchlar mavjud |
| `S0-02` | `requirements/` bo'linishi, virtualenv | 1 | `pip install -r requirements/local.txt` ishlaydi |
| `S0-03` | `config/settings/` bo'linishi + `python-decouple`/`django-environ` | 2 | `.env.example` bor, secret kod ichida yo'q |
| `S0-04` | Docker Compose: web + db + redis | 3 | `docker compose up` bilan loyiha ko'tariladi |
| `S0-05` | `common` app: `BaseModel`, custom exception handler, pagination | 3 | Har qanday xato yagona formatda qaytadi |
| `S0-06` | `drf-spectacular` sozlash | 1 | `/api/docs/` ochiladi |
| `S0-07` | pre-commit: ruff + black + isort | 1 | commit'da avtomatik lint |
| `S0-08` | GitHub Actions: lint + test | 2 | PR'da CI yashil bo'ladi |

---

### 🟩 Sprint 1 — Auth + Telegram bot (1 hafta) ⭐ eng muhim

| ID | Task | Soat | DoD |
|---|---|---|---|
| `S1-01` | Custom `User` model + `UserManager` (`create_user`, `create_superuser`) | 4 | `createsuperuser` phone bilan ishlaydi |
| `S1-02` | Telefon normalizatsiya utili + validator | 2 | `998901234567`, `901234567`, `+998 90 123 45 67` → bir xil natija; testlar bor |
| `S1-03` | `VerificationCode` model + kod generator service | 3 | `expires_at` avtomatik +5 daq |
| `S1-04` | `POST /auth/register/` | 4 | `is_active=False`, parol hash'langan, dublikat phone/email 400 qaytaradi |
| `S1-05` | Aiogram bot: `/start` + contact tugmasi | 5 | Raqam yuborilsa `telegram_id` saqlanadi |
| `S1-06` | Bot ↔ Django integratsiya (kod yaratish va yuborish) | 4 | Botda 6 xonali kod keladi |
| `S1-07` | `POST /auth/confirm/` | 3 | Muddati o'tgan/ishlatilgan/xato kod aniq xabar bilan rad etiladi |
| `S1-08` | `POST /auth/resend-code/` + throttle | 3 | Yaroqli kod bor bo'lsa yangi kod bermaydi |
| `S1-09` | `POST /auth/login/` (custom JWT serializer) | 3 | 3 xil xato holati 3 xil javob |
| `S1-10` | `token/refresh/`, `logout/` (blacklist) | 2 | Logout'dan keyin refresh ishlamaydi |
| `S1-11` | Reset password (2 ta endpoint) | 4 | Parol o'zgargach eski tokenlar bekor |
| `S1-12` | `GET/PATCH /auth/me/` + avatar upload | 3 | Avatar hajmi/format validatsiyasi bor |
| `S1-13` | `role='admin'` → `is_staff=True` avtomatlashtirish | 1 | Admin paneldan rol o'zgartirilsa ishlaydi |
| `S1-14` | Auth testlari (pytest) | 5 | Kamida 15 ta test, coverage ≥ 80% |
| `S1-15` | Celery task: eskirgan kodlarni tozalash (beat, kuniga 1 marta) | 2 | Task loglanadi |

**Sprint 1 demo:** Postman'da register → botda kod → confirm → login → me.

---

### 🟨 Sprint 2 — Katalog (1 hafta)

| ID | Task | Soat | DoD |
|---|---|---|---|
| `S2-01` | `Category`, `SubCategory`, `Unit` modellari + admin | 3 | slug avtomatik |
| `S2-02` | `Product` + `ProductImage` modellari | 4 | `is_main` bittadan ko'p bo'lmaydi |
| `S2-03` | Boshlang'ich data (`fixtures` yoki management command): 6 kategoriya, 20+ subkategoriya, 7 unit | 3 | `python manage.py seed_catalog` |
| `S2-04` | Katalog serializerlari (list ≠ detail) | 4 | List'da og'ir maydonlar yo'q |
| `S2-05` | `GET /products/` + `django-filter` + search + ordering | 5 | Barcha filterlar Swagger'da ko'rinadi |
| `S2-06` | `GET /products/{slug}/` + `views_count` oshirish (`F()` bilan) | 2 | Race condition yo'q |
| `S2-07` | Admin CRUD: category, subcategory, unit, product | 6 | Faqat `role=admin` kira oladi |
| `S2-08` | Rasm yuklash/o'chirish endpointi | 3 | Multipart ishlaydi |
| `S2-09` | **N+1 audit**: `select_related` / `prefetch_related` | 3 | `django-debug-toolbar`da list sahifada ≤ 5 query |
| `S2-10` | Katalog testlari | 4 | Filter va permission testlari bor |

---

### 🟧 Sprint 3 — Like, Comment, Savatcha (1 hafta)

| ID | Task | Soat | DoD |
|---|---|---|---|
| `S3-01` | `Like` model + toggle endpoint | 3 | Ikki marta bosilsa o'chadi, DB'da dublikat yo'q |
| `S3-02` | Mahsulot listida `likes_count` va `is_liked` (annotate) | 3 | Qo'shimcha query yo'q |
| `S3-03` | `Comment` model + CRUD | 4 | Faqat egasi tahrirlaydi/o'chiradi |
| `S3-04` | Comment'ga javob (`parent`) | 3 | 1 daraja chuqurlik yetarli |
| `S3-05` | `Cart` avtomatik yaratish (signal yoki `get_or_create`) | 2 | Har userda 1 ta savat |
| `S3-06` | Savatcha CRUD endpointlari | 5 | Mavjud mahsulot qayta qo'shilsa `quantity` qo'shiladi |
| `S3-07` | Savatchada zaxira tekshiruvi | 3 | `quantity > product.quantity` bo'lsa 400 |
| `S3-08` | Savat summasi hisoblash (aggregate) | 2 | `total_items`, `total_price` |
| `S3-09` | Testlar | 4 | |

---

### 🟥 Sprint 4 — Buyurtma + Ombor (1 hafta)

| ID | Task | Soat | DoD |
|---|---|---|---|
| `S4-01` | `Order`, `OrderItem`, `OrderStatusHistory` modellari | 4 | |
| `S4-02` | `order_number` generator | 2 | Unique, `ORD-YYYYMMDD-NNNN` |
| `S4-03` | **`create_order` service** — `transaction.atomic` + `select_for_update` | 6 | Bir vaqtda 2 buyurtma kelsa zaxira minusga tushmaydi |
| `S4-04` | Buyurtma yaratilganda: savat tozalanadi, narx snapshot olinadi, `StockMovement(out)` yoziladi | 4 | `product.quantity` mos kamayadi |
| `S4-05` | `GET /orders/`, `GET /orders/{id}/` | 3 | User faqat o'zinikini ko'radi |
| `S4-06` | `POST /orders/{id}/cancel/` + zaxira qaytarish | 3 | Faqat ruxsat etilgan statuslarda |
| `S4-07` | `StockMovement` model + kirim endpointi | 4 | Kirimda `product.quantity` oshadi |
| `S4-08` | `Return` model + qaytarish so'rovi | 4 | Approve bo'lsa zaxira qaytadi |
| `S4-09` | Admin: buyurtma statusini o'zgartirish + history | 4 | Noto'g'ri o'tish (masalan `delivered → new`) bloklanadi |
| `S4-10` | Status o'zgarganda botga xabar (Celery task) | 3 | `telegram_id` bo'lsa yuboriladi |
| `S4-11` | Testlar (ayniqsa concurrency) | 5 | |

**Status oqimi:**
```
new → confirmed → shipping → delivered
 ↓        ↓
cancelled cancelled
delivered → returned
```

---

### 🟪 Sprint 5 — Admin panel API + Statistika (1 hafta)

| ID | Task | Soat | DoD |
|---|---|---|---|
| `S5-01` | `IsAdminRole` permission + `/admin-api/` router | 2 | Oddiy user 403 oladi |
| `S5-02` | `/stats/overview/` (day/week/month) | 5 | Bitta query'da aggregate |
| `S5-03` | `/stats/sales/` grafik uchun (`TruncDate` bilan) | 5 | Bo'sh kunlar ham 0 bilan qaytadi |
| `S5-04` | `/stats/products/top-selling/` va `least-selling/` | 4 | Miqdor va summa bo'yicha ikkalasi |
| `S5-05` | `/stats/products/most-viewed/`, `most-liked/` | 3 | |
| `S5-06` | `/stats/products/most-returned/` | 3 | `Return(approved)` bo'yicha |
| `S5-07` | `/stats/inventory/`, `low-stock/`, `out-of-stock/` | 4 | "Yana qancha kerak" = `min_quantity − quantity` |
| `S5-08` | `/stats/users/active/`, `top-customers/` | 4 | |
| `S5-09` | `/stats/orders/by-status/` | 2 | |
| `S5-10` | Redis cache + invalidatsiya | 4 | Yangi buyurtmada cache tozalanadi |
| `S5-11` | Admin: userlar ro'yxati, block/unblock | 3 | |
| `S5-12` | Django admin panelini sozlash (`list_display`, `search_fields`, `list_filter`, `readonly`) | 4 | Rol shu yerdan o'zgartiriladi |
| `S5-13` | Statistika testlari (aniq raqamlar bilan) | 5 | Fixture data → kutilgan natija |

---

### ⬜ Sprint 6 — Sifat, hujjat, deploy (1 hafta)

| ID | Task | Soat | DoD |
|---|---|---|---|
| `S6-01` | Swagger'ni to'liq tozalash: har endpointda `summary`, `description`, `examples` | 6 | AI shu doc bilan frontend yoza oladi |
| `S6-02` | Postman collection eksport | 2 | Repo'da `docs/postman.json` |
| `S6-03` | N+1 va sekin querylarni audit (`django-silk` yoki `debug-toolbar`) | 5 | Har endpoint ≤ 200ms (lokalda) |
| `S6-04` | Kerakli indekslarni qo'shish | 3 | `EXPLAIN ANALYZE` bilan isbot |
| `S6-05` | Throttling: anon 60/min, user 300/min, auth-scoped alohida | 2 | |
| `S6-06` | CORS, `ALLOWED_HOSTS`, `DEBUG=False` tekshiruvi | 2 | |
| `S6-07` | Media/static: whitenoise + nginx yoki S3 | 3 | |
| `S6-08` | Coverage ≥ 75% | 6 | CI'da tekshiriladi |
| `S6-09` | README: o'rnatish, `.env`, arxitektura, ERD rasm | 4 | Yangi odam 15 daqiqada ko'taradi |
| `S6-10` | Deploy (VPS + docker-compose + nginx + certbot) | 6 | Domen orqali `https` ishlaydi |

---

### 🤖 Sprint 7 — Frontend / Mobile (AI orqali, 1 hafta)

| ID | Task | Kim |
|---|---|---|
| `S7-01` | OpenAPI schema'ni eksport qilish (`schema.yaml`) | Backend |
| `S7-02` | AI'ga aniq prompt: rol, sahifalar ro'yxati, dizayn tili, API schema | Mentor |
| `S7-03` | Web: Next.js/React — katalog, mahsulot, savat, buyurtma, profil, admin dashboard | AI |
| `S7-04` | Mobile: Flutter/React Native — katalog, savat, buyurtma, profil | AI |
| `S7-05` | Integratsiya bug'larini backendda tuzatish | O'quvchilar |
| `S7-06` | E2E qo'lda test: register → confirm → login → zakaz → admin status | Jamoa |

> Frontend uchun kerak bo'ladigan backend qo'shimchalari (oldindan qiling): CORS, `is_liked` flag, `total` maydonlar, tasvirlar uchun to'liq URL, xatolik matnlari o'zbekcha.

---

## 8. Jamoa taqsimoti

4 kishilik guruh nazarda tutilgan. Har kim **o'z moduli egasi**, lekin PR'ni boshqa a'zo review qiladi.

| Guruh | Mas'ul modul | Sprintlar |
|---|---|---|
| **A — Auth & Bot** | `users`, `bot`, permissions | S1 asosiy, keyin bot xabarnomalar |
| **B — Catalog** | `catalog`, `interactions` | S2, S3 |
| **C — Orders & Inventory** | `orders`, `inventory` | S3 (savat), S4 |
| **D — Admin & Analytics** | `analytics`, admin-api, Django admin | S5 |

`common`, Docker, CI — **hammasi birga**, Sprint 0 da.

**Rotatsiya qoidasi:** Sprint 6 da har kim boshqa odamning modulini test bilan qoplaydi — shunda hamma butun kodni ko'radi.

---

## 9. Git workflow

```
main       ← faqat release
develop    ← integratsiya
feature/S1-04-register-api
fix/S2-06-views-count-race
```

**Commit format (Conventional Commits):**
```
feat(users): register endpoint qo'shildi
fix(orders): zaxira minusga tushishi tuzatildi
test(catalog): filter testlari
refactor(analytics): aggregate optimizatsiya
```

**PR qoidalari:**
- 1 task = 1 PR (400 qatordan oshmasin)
- Tavsifda: nima qilindi, qanday test qilindi, screenshot/Postman natija
- CI yashil + 1 reviewer approve → merge
- `develop` ga to'g'ridan-to'g'ri push **taqiqlanadi**

---

## 10. Definition of Done (har bir task uchun)

Task "tugadi" deyilishi uchun **hammasi** bajarilishi shart:

- [ ] Kod ishlaydi va lokalda qo'lda tekshirilgan
- [ ] Migratsiya yaratilgan va konfliktsiz
- [ ] Serializer validatsiyasi bor (bo'sh, salbiy, juda uzun qiymatlar)
- [ ] Permission to'g'ri (anon / user / admin uchun alohida sinalgan)
- [ ] Xatolik matnlari **o'zbekcha** va tushunarli
- [ ] Kamida 2 ta test: happy path + xato holat
- [ ] N+1 yo'q (`select_related`/`prefetch_related`)
- [ ] Swagger'da endpoint to'g'ri ko'rinadi
- [ ] `ruff` va `black` toza
- [ ] PR review'dan o'tgan

---

## 11. Tez-tez uchraydigan xatolar (oldindan ogohlantirish)

| # | Xato | To'g'ri yechim |
|---|---|---|
| 1 | Buyurtmada `product.price` ni o'qish | `OrderItem.price` snapshot |
| 2 | Zaxirani `product.quantity -= x` deb yozish | `select_for_update()` + `transaction.atomic` + `F()` |
| 3 | Statistikani Python loop bilan hisoblash | ORM `aggregate`/`annotate` |
| 4 | `Like` da dublikat | `unique_together` + `get_or_create` |
| 5 | Mahsulotni `on_delete=CASCADE` bilan o'chirish | `PROTECT` yoki `is_active=False` (soft delete) |
| 6 | Kodni API javobida qaytarish | Faqat botga yuborish |
| 7 | Har turli telefon formati | Bitta normalizatsiya funksiyasi, serializer'da chaqiriladi |
| 8 | `views_count += 1` (race) | `F('views_count') + 1` |
| 9 | Business logic view ichida | `services.py` |
| 10 | `.env` ni git'ga qo'shish | `.gitignore` + `.env.example` |
| 11 | Decimal o'rniga `float` (pul uchun) | `DecimalField` |
| 12 | Kirim/chiqimni yozib qo'ymaslik | Har o'zgarish `StockMovement` orqali |

---

## 12. Baholash mezonlari (mentor uchun, 100 ball)

| Mezon | Ball |
|---|---|
| Funksional to'liqlik (TZ bo'yicha barcha endpointlar) | 30 |
| Ma'lumotlar modeli va migratsiyalar sifati | 10 |
| Auth va xavfsizlik (throttle, permission, token) | 15 |
| Statistika to'g'riligi va ORM optimizatsiyasi | 15 |
| Test coverage va testlar sifati | 10 |
| Kod tozaligi, struktura, `services.py` ajratilishi | 10 |
| Git tarixi va PR madaniyati | 5 |
| Hujjat (Swagger, README) | 5 |

**Bonus (+10):** WebSocket orqali admin dashboard real-time · Excel eksport (`openpyxl`) · Elasticsearch search · Docker prod optimizatsiya (multi-stage) · Sentry integratsiya.

---

## 13. Kalendar (taxminiy 7 hafta)

| Hafta | Sprint | Demo |
|---|---|---|
| 1 | S0 + S1 boshlanishi | Loyiha ko'tariladi, register ishlaydi |
| 2 | S1 tugashi | To'liq auth + bot |
| 3 | S2 | Katalog + filter |
| 4 | S3 | Like, comment, savat |
| 5 | S4 | Buyurtma + ombor |
| 6 | S5 | Statistika dashboard API |
| 7 | S6 + S7 | Deploy + frontend |

**Har hafta juma:** 40 daqiqalik demo + 20 daqiqa code review sessiyasi.

---

## 14. Keyingi qadam

1. Ushbu hujjatni GitHub Projects / Trello'ga ko'chiring (har task — alohida karta, ID bilan).
2. Sprint 0 ni **birga**, ekranda ko'rsatib bajaring — hamma bir xil bazadan boshlasin.
3. ERD chizmasini (dbdiagram.io) chizib repo'ga qo'ying.
4. Sprint 1 ni boshlashdan oldin 30 daqiqa: "custom User model nega kerak" mavzusida mini-dars.
