# Abstract Webhook Checklist (Django `webhooks`)

## 1) Maqsad
Bu hujjat `paytechuz/integrations/django/webhooks/` dagi amaldagi logikadan kelib chiqib tuzilgan.
Maqsad: yangi provider qo‘shilganda webhook abstraksiyasida hech bir muhim nuqta tushib qolmasligi.

---

## 2) Hozirgi implementatsiyadan umumiy oqim (common flow)
Quyidagi oqim deyarli barcha providerlarda bor:

1. `__init__`:
   - `settings.PAYTECHUZ[PROVIDER_KEY]` dan konfiguratsiya o‘qish
   - `ACCOUNT_MODEL` ni `import_string(...)` bilan resolve qilish
   - `ACCOUNT_FIELD`, `AMOUNT_FIELD`, `ONE_TIME_PAYMENT` kabi sozlamalarni olish

2. `post(...)`:
   - request parse (`JSON` yoki `form`)
   - autentifikatsiya/signature verifikatsiya
   - provider method/action dispatch
   - account topish
   - amount validatsiya
   - `PaymentTransaction` yaratish/topish/yangilash
   - state transition (`CREATED`, `INITIATING`, `SUCCESSFULLY`, `CANCELLED`, `CANCELLED_DURING_INIT`)
   - hook methodlarni chaqirish (`successfully_payment`, `cancelled_payment`, ...)
   - provider formatida response qaytarish

3. Error handling:
   - ichki exception -> provider-specific error code/message mapping
   - ayrim providerlar `HTTP 200` bilan error qaytaradi, ayrimlari `4xx`

---

## 3) Providerlar bo‘yicha minimal farqlar (abstraksiya uchun)

1. Payme:
   - JSON-RPC (`method` orqali dispatch)
   - Basic auth (asosan merchant key)
   - Amount odatda tiyin (`amount`) formatida keladi
   - Methodlar: `CheckPerformTransaction`, `CreateTransaction`, `PerformTransaction`, `CheckTransaction`, `CancelTransaction`, `GetStatement`

2. Click:
   - `request.POST` form-data
   - `md5` signature (`sign_string`) verifikatsiya
   - `action=0/1` (prepare/complete)
   - response format Click kodlari bilan (`error`, `error_note`)

3. Uzum:
   - URL action (`check/create/confirm/reverse/status`)
   - Basic auth (username/password)
   - `serviceId` tekshiruvi majburiy
   - statuslar string (`OK`, `CREATED`, `CONFIRMED`, `REVERSED`, `FAILED`)

4. Paynet:
   - JSON-RPC
   - Basic auth (username/password)
   - `serviceId` tekshiruvi
   - methodlar: `PerformTransaction`, `CheckTransaction`, `CancelTransaction`, `GetStatement`, `GetInformation`, `ChangePassword`

5. Octo:
   - callback JSON
   - signature: `sha1(unique_key + octo_payment_UUID + status)`
   - `TEST_MODE=True` bo‘lsa signature check skip qilinadi
   - asosiy statuslar: `succeeded`, `canceled`, `failed`

---

## 4) Abstract webhook kontraktida majburiy bo‘lishi kerak bo‘lgan checklar

### A. Security va kirish nazorati
1. Auth/signature tekshiruv har doim request parse qilinganidan keyin va business-logikadan oldin ishlasin.
2. Provider identity (`serviceId`, `merchant_id`, shop id va h.k.) tekshirilsin.
3. `TEST_MODE` ga bog‘liq security istisnolari aniq log qilinsin.
4. Noto‘g‘ri auth bo‘lsa provider protokoli bo‘yicha to‘g‘ri error qaytarilsin.

### B. Request validatsiya
1. Majburiy fieldlar (`id`, `method`, `params`, `amount`, `transactionId`, ...) tekshirilsin.
2. JSON parse/form parse xatolari alohida error code bilan qaytsin.
3. Type-casting xavfsiz bo‘lsin (`int/Decimal/float` conversionlarda aniq exception handling).

### C. Account resolution
1. `ACCOUNT_MODEL` import xatolari fail-fast bo‘lsin.
2. `ACCOUNT_FIELD` bo‘yicha lookup har provider uchun bir xil tamoyilda ishlasin.
3. `id` string/int konversiyasi bir xil qoida asosida bo‘lsin.
4. Account topilmasa providerga mos error code qaytarilsin.

### D. Amount va valyuta birligi
1. `AMOUNT_FIELD` ishlatilishi providerlarda bir xil standartga keltirilsin.
2. Minor/major unit (tiyin/som) conversion qoidasi aniq yozilsin.
3. `ONE_TIME_PAYMENT=True` bo‘lsa strict amount match va duplicate paid check bo‘lsin.
4. `ONE_TIME_PAYMENT=False` bo‘lsa minimal valid amount qoidasi bo‘lsin (`> 0` va h.k.).

### E. Transaction lifecycle va idempotency
1. `gateway + transaction_id` unique bo‘yicha duplicate callback xavfsiz boshqarilsin.
2. Final holatdagi transaction (`SUCCESSFULLY/CANCELLED`) qayta callbackda qayta ishlanmasin.
3. State transitionlar faqat ruxsat etilgan yo‘nalishlarda bo‘lsin.
5. `extra_data` update merge-safe bo‘lsin (eski ma’lumot yo‘qolmasin).

### F. Response mapping
1. Har providerning protokol formati saqlansin (JSON-RPC vs plain JSON vs form response).
2. Internal exception -> provider error code mapping jadvali bo‘lsin.
3. HTTP status siyosati provider bo‘yicha aniq (200 vs 4xx).
4. `request_id/rpc_id` mavjud bo‘lmagan holatda ham deterministik response qaytsin.

### G. Hooks/extension points
1. Har providerda override qilinadigan hooklar aniq ro‘yxatda bo‘lsin:
   - `successfully_payment`
   - `cancelled_payment`
   - providerga xos: `transaction_created`, `transaction_already_exists`, `before_check_perform_transaction`, `get_check_data`, `get_statement`, `check_transaction`
2. Hooklar chaqirilish tartibi hujjatlashtirilsin.
3. Hook ichidagi exceptionlar asosiy response protokolini buzmasligi ko‘rib chiqilsin.

### H. Logging va audit
1. Har request uchun tracega yetarli data loglansin (maxfiy ma’lumotni maskalab).
2. Security xatolari (`invalid signature/auth`) alohida warning/error sifatida chiqsin.
3. State o‘zgarishi audit loglari kuzatiladigan bo‘lsin.

---

## 5) Yangi provider qo‘shishda “hech narsa qolmasligi” checklist

1. `webhooks/<provider>.py` yaratildi va provider protokoli to‘liq implement qilindi.
2. `paytechuz/integrations/django/webhooks/__init__.py` export yangilandi.
3. `paytechuz/integrations/django/webhooks/__init__.py` da export qo‘shildi.
4. `paytechuz/integrations/django/views.py` da `Base<Provider>WebhookView` qo‘shildi (`csrf_exempt`).
5. `PAYTECHUZ` settings uchun provider schema README va kodda bir xil bo‘ldi.
6. `PaymentTransaction` gateway choice yangilandi (`models.py`) va migration strategiyasi ko‘rib chiqildi.
7. Zarur bo‘lsa `factory.py`, `core/constants.py`, package export (`__init__.py`) yangilandi.
8. Error code constants (agar alohida faylda bo‘lsa) qo‘shildi.
9. URL pattern namunalari README da qo‘shildi.
10. Testlar yozildi (kamida quyidagi regressionlar):
    - valid auth + success flow
    - invalid auth/signature
    - account not found
    - invalid amount
    - duplicate callback/idempotency
    - cancel/reverse flow
    - one-time payment conflict
    - parse error (invalid json/form)

---

## 6) Abstraksiya uchun tavsiya etilgan minimal interfeys

1. `parse_request(request) -> ParsedPayload`
2. `authenticate(request, payload) -> None`
3. `validate_provider_context(payload) -> None`  (service/shop/merchant)
4. `resolve_account(payload) -> account`
5. `validate_amount(payload, account) -> None`
6. `resolve_transaction(payload, account) -> transaction`
7. `apply_state_transition(payload, transaction) -> transaction`
8. `build_success_response(payload, transaction) -> JsonResponse`
9. `map_exception(exc, payload) -> JsonResponse`

Bu interfeys provider-specific classlarda override qilinadi, lekin transaction/idempotency/security siyosati markaziy bazada qoladi.

---

## 7) Hozirgi koddan kelib chiqqan risk-checklar (albatta tekshirish kerak)

1. `AMOUNT_FIELD` barcha providerlarda bir xil darajada ishlatilganmi (hardcode yo‘qmi)?
2. Amount unit conversion (tiyin/som) barcha providerlarda bir xil siyosatdami?
3. `factory.py` va gateway enum/exportlar o‘zaro mosmi?
4. Django migrationlarda gateway choices amaldagi model bilan mosmi?
5. Hooklar chaqirilishida double-call yoki missed-call yo‘qmi?

Bu bandlar yangi provider qo‘shishda eng ko‘p regressiya beradigan nuqtalar.
