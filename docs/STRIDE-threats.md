# STRIDE: Анализ угроз для потоков данных

| ID | Поток данных (DFD) | Категория STRIDE | Угроза | Меры защиты | Контроли NFR |
|----|-------------------|------------------|--------|-------------|--------------|
| **T-1** | DF-1: User Credentials<br/>(Client → Auth Service) | **Spoofing** | Перехват креденшелов через MitM, фишинг, подмена пользователя | • HTTPS/TLS 1.3 обязательно<br/>• Rate limiting: 5 req/min на IP<br/>• Хеширование паролей (bcrypt)<br/>• Correlation ID для аудита | NFR-06 (JWT Auth)<br/>NFR-08 (Rate Limiting)<br/>NFR-02 (Logging) |
| **T-2** | DF-2: JWT Tokens<br/>(Auth Service → Client) | **Tampering** | Подделка JWT токена, изменение payload (роль, owner_id, exp) | • JWT HS256 подпись с SECRET_KEY<br/>• Верификация подписи при каждом запросе<br/>• Проверка issuer/audience claims<br/>• Clock skew ±60s | NFR-06 (JWT Signature)<br/>NFR-05 (Secret Rotation) |
| **T-3** | DF-3: Highlight CRUD<br/>(Client → Highlights API) | **Repudiation** | Отрицание создания/изменения записи, отсутствие доказательств действий | • Логирование всех операций с correlation_id<br/>• Аудит с привязкой к sub (user ID)<br/>• Неизменяемые логи с timestamps | NFR-02 (Correlation ID)<br/>NFR-01 (RFC 7807 Errors)<br/>NFR-10 (API Contract) |
| **T-4** | DF-4: File Uploads<br/>(Client → Upload Service → S3) | **Information Disclosure** | Утечка файлов через path traversal, доступ к чужим файлам, раскрытие temp paths | • UUID v4 генерация ключей S3<br/>• Канонизация путей (Path.resolve)<br/>• Проверка префикса TMP_DIR<br/>• S3 bucket policy (private)<br/>• Фильтрация по owner_id | NFR-04 (File Security)<br/>NFR-07 (Ownership)<br/>TB-2 (S3 Encryption) |
| **T-5** | DF-5: Secret Retrieval<br/>(Auth Service → Secret Manager) | **Denial of Service** | Исчерпание лимитов Secret Manager API, блокировка выдачи токенов | • Кеширование секретов в памяти<br/>• Dual-key support (текущий + предыдущий)<br/>• Timeout на запросы к Secret Manager<br/>• Graceful degradation при ошибках | NFR-05 (Secret Management)<br/>NFR-08 (Performance)<br/>NFR-06 (Dual-key Rotation) |
| **T-6** | DF-6: Error Responses<br/>(Error Handler → Client) | **Information Disclosure** | Утечка stack traces, путей файлов, версий библиотек, конфиденциальных данных в ошибках | • RFC 7807 стандарт ошибок<br/>• Маскирование секретов в логах<br/>• Generic error messages для 500<br/>• Отсутствие stack traces в продакшене | NFR-01 (RFC 7807)<br/>NFR-02 (Secret Masking)<br/>TB-1 (No Enumeration) |
| **T-7** | DF-3: Highlight GET/DELETE<br/>(Client → Highlights API → Storage) | **Elevation of Privilege** | Доступ к чужим highlights через IDOR, горизонтальное повышение привилегий | • RBAC: роли user/admin<br/>• Фильтрация owner_id на уровне Storage<br/>• Default deny policy<br/>• 404 вместо 403 (анти-перечисление) | NFR-07 (Authorization)<br/>TB-1.2 (Ownership Check)<br/>P-5 (AuthZ Process) |
| **T-8** | DF-4: File Upload Validation<br/>(Upload Service → TmpDir) | **Tampering** | Polyglot файлы, magic bytes spoofing, ZIP bomb, загрузка исполняемых файлов | • Magic bytes валидация (PNG: 8 байт, JPEG: start+end)<br/>• MIME type vs signature matching<br/>• Размер ≤ 5MB, timeout 30s<br/>• Rate limiting: 3 req/min/user<br/>• Только PNG/JPEG, запрет SVG | NFR-04 (File Validation)<br/>NFR-08 (Rate Limiting)<br/>TB-1.2 (Magic Bytes)<br/>AS-1,4,5,6 (Attack Scenarios) |

## Легенда

### Категории STRIDE
- **S**poofing — Подмена идентичности
- **T**ampering — Искажение данных
- **R**epudiation — Отказ от действий
- **I**nformation Disclosure — Раскрытие информации
- **D**enial of Service — Отказ в обслуживании
- **E**levation of Privilege — Повышение привилегий

### Ссылки на документацию
- **NFR-XX** — Non-Functional Requirements из [README-nfr.md](./README-nfr.md)
- **TB-X** — Trust Boundaries из DFD диаграм
- **DF-X** — Data Flows из [DFD-0-context.md](./dfd/DFD-0-context.md)
- **AS-X** — Attack Scenarios из [DFD-2](./dfd/DFD-2-authentication.md) и [DFD-3](./dfd/DFD-3-file-upload.md)
- **P-X** — Processes из [DFD-1-application.md](./dfd/DFD-1-application.md)

## Приоритизация угроз

| Угроза | Вероятность | Воздействие | Приоритет | Статус |
|--------|-------------|-------------|-----------|--------|
| T-1 (Credential Spoofing) | Высокая | Критическое | **P0** | Защищено |
| T-2 (JWT Tampering) | Средняя | Критическое | **P0** | Защищено |
| T-7 (IDOR) | Высокая | Высокое | **P1** | Защищено |
| T-8 (Malicious Upload) | Средняя | Высокое | **P1** | Защищено |
| T-4 (File Disclosure) | Средняя | Среднее | **P2** | Защищено |
| T-6 (Error Leakage) | Низкая | Среднее | **P2** | Защищено |
| T-3 (Repudiation) | Низкая | Низкое | **P3** | Защищено |
| T-5 (Secret Manager DoS) | Низкая | Среднее | **P3** | Защищено |

## Меры безопасности с трассировкой

### Таблица мер (Security Controls)

| ID | Мера безопасности | Описание | Покрываемые угрозы | Реализация | NFR | Тесты |
|----|-------------------|----------|-------------------|------------|-----|-------|
| **M-1** | TLS/HTTPS Only | Принудительное использование HTTPS/TLS 1.3+ для всех соединений | T-1, T-4, T-6 | • Конфигурация Load Balancer<br/>• HSTS заголовки<br/>• Редирект HTTP→HTTPS | NFR-06 | E2E: проверка HTTPS |
| **M-2** | Rate Limiting | Ограничение частоты запросов по IP/пользователю | T-1, T-5, T-8 | • Login: 5 req/min/IP<br/>• Token refresh: 5 req/min/IP<br/>• POST highlights: 10 req/min/IP<br/>• Upload: 3 req/min/user | NFR-08 | Unit: `test_rate_limiter.py` |
| **M-3** | JWT Signature Verification | Проверка подписи HS256 с SECRET_KEY | T-2, T-7 | • При каждом защищенном запросе<br/>• Проверка issuer/audience<br/>• Clock skew ±60s<br/>• Поддержка ротации (dual-key) | NFR-06 | Unit: `test_jwt_verify.py` |
| **M-4** | Correlation ID | Генерация уникального ID для каждого запроса | T-3 | • Middleware добавляет correlation_id<br/>• Логируется во всех операциях<br/>• Возвращается в ошибках RFC 7807 | NFR-02 | Integration: проверка заголовков |
| **M-5** | Owner-based Filtering | Автоматическая фильтрация по owner_id | T-4, T-7 | • Storage.list() фильтрует по owner_id<br/>• Storage.get() проверяет владельца<br/>• 404 вместо 403 (анти-перечисление) | NFR-07 | Unit: `test_authorization.py` |
| **M-6** | RFC 7807 Error Format | Стандартизированный формат ошибок без утечек | T-6 | • Все 4xx/5xx в формате problem+json<br/>• Маскирование секретов в логах<br/>• Generic messages для 500 | NFR-01, NFR-02 | Contract: `test_error_format.py` |
| **M-7** | File Magic Bytes Validation | Проверка сигнатур файлов | T-8 | • PNG: 8 байт `89 50 4E 47 0D 0A 1A 0A`<br/>• JPEG: FFD8FF + FFD9 в конце<br/>• MIME type vs signature matching | NFR-04 | Unit: `test_file_validator.py` |
| **M-8** | Path Canonicalization | Предотвращение path traversal | T-4, T-8 | • UUID v4 для имен файлов<br/>• Path.resolve(strict=True)<br/>• Проверка префикса TMP_DIR<br/>• Обнаружение symlinks | NFR-04 | Unit: `test_path_security.py` |
| **M-9** | S3 Server-Side Encryption | Шифрование файлов в S3 | T-4 | • AES256 шифрование<br/>• UUID object keys<br/>• Private bucket policy<br/>• Metadata (owner_sub, correlation_id) | NFR-04, TB-2 | Integration: S3 mock |
| **M-10** | Secret Rotation Support | Бесшовная ротация JWT ключей | T-2, T-5 | • SECRET_KEY + SECRET_KEY_PREV<br/>• Верификация обоими ключами<br/>• Выдача только текущим<br/>• Кеширование секретов | NFR-05, NFR-06 | Unit: `test_secret_rotation.py` |
| **M-11** | Input Validation | Строгая валидация входных данных | T-8 | • Pydantic схемы<br/>• text ≤ 2000, source ≤ 500<br/>• tags ≤ 10, lowercase, trim<br/>• Санитизация HTML/скриптов | NFR-03 | Unit: `test_validation.py` |
| **M-12** | Token Denylist | Отзыв refresh токенов | T-2 | • In-memory set с jti<br/>• Проверка при refresh<br/>• Добавление при logout<br/>• Периодическая очистка | NFR-06 | Unit: `test_token_revocation.py` |
| **M-13** | RBAC Authorization | Контроль доступа на основе ролей | T-7 | • Роли: user/admin<br/>• Default deny policy<br/>• Scope проверка (опц.)<br/>• Admin bypass для owner checks | NFR-07 | Unit: `test_rbac.py` |
| **M-14** | Size & Timeout Limits | Ограничения размера и времени | T-5, T-8 | • File size ≤ 5MB<br/>• Upload timeout ≤ 30s<br/>• Request body limit | NFR-04, NFR-08 | Integration: large file test |

### Трассировка угроз к мерам

| Угроза | Меры защиты | Покрытие |
|--------|-------------|----------|
| **T-1** (Credential Spoofing) | M-1 (HTTPS), M-2 (Rate Limit), M-4 (Correlation) | Полное |
| **T-2** (JWT Tampering) | M-3 (JWT Verify), M-10 (Rotation), M-12 (Denylist) | Полное |
| **T-3** (Repudiation) | M-4 (Correlation ID), M-6 (RFC 7807) | Полное |
| **T-4** (File Disclosure) | M-1 (HTTPS), M-5 (Owner Filter), M-8 (Path Canon), M-9 (S3 Encryption) | Полное |
| **T-5** (Secret Manager DoS) | M-2 (Rate Limit), M-10 (Caching + Dual-key), M-14 (Timeout) | Полное |
| **T-6** (Error Leakage) | M-1 (HTTPS), M-6 (RFC 7807 + Masking) | Полное |
| **T-7** (IDOR / Privilege Escalation) | M-3 (JWT Verify), M-5 (Owner Filter), M-13 (RBAC) | Полное |
| **T-8** (Malicious Upload) | M-2 (Rate Limit), M-7 (Magic Bytes), M-8 (Path Canon), M-11 (Validation), M-14 (Size Limit) | Полное |

### Трассировка мер к функциональности (User Stories)

Поскольку явные User Stories отсутствуют, привязка к функциональным возможностям API:

| Функция | Endpoint | Меры | Угрозы |
|---------|----------|------|--------|
| **F-1: Аутентификация** | `POST /auth/login` | M-1, M-2, M-3, M-4, M-10 | T-1, T-2 |
| **F-2: Обновление токена** | `POST /auth/token` | M-2, M-3, M-10, M-12 | T-2, T-5 |
| **F-3: Выход (отзыв токена)** | `POST /auth/logout` | M-3, M-12 | T-2, T-3 |
| **F-4: Создание highlight** | `POST /highlights` | M-2, M-3, M-4, M-5, M-11, M-13 | T-3, T-7 |
| **F-5: Чтение highlights** | `GET /highlights` | M-3, M-5, M-13 | T-7 |
| **F-6: Получение highlight** | `GET /highlights/{id}` | M-3, M-5, M-13 | T-7 |
| **F-7: Обновление highlight** | `PUT /highlights/{id}` | M-3, M-5, M-11, M-13 | T-7 |
| **F-8: Удаление highlight** | `DELETE /highlights/{id}` | M-3, M-5, M-13 | T-7 |
| **F-9: Загрузка файла** | `POST /upload` (future) | M-1, M-2, M-3, M-7, M-8, M-9, M-11, M-14 | T-4, T-8 |
| **F-10: Экспорт в Markdown** | `GET /highlights/export/markdown` | M-3, M-5 | T-7 |

### Матрица соответствия: NFR ↔ Меры ↔ Угрозы

| NFR | Меры | Угрозы |
|-----|------|--------|
| NFR-01 (RFC 7807) | M-6 | T-3, T-6 |
| NFR-02 (Correlation & Logging) | M-4, M-6 | T-3, T-6 |
| NFR-03 (Input Validation) | M-11 | T-8 |
| NFR-04 (File Security) | M-7, M-8, M-9, M-14 | T-4, T-8 |
| NFR-05 (Secret Management) | M-10 | T-2, T-5 |
| NFR-06 (JWT Auth) | M-3, M-10, M-12 | T-1, T-2 |
| NFR-07 (Authorization) | M-5, M-13 | T-4, T-7 |
| NFR-08 (Performance & RL) | M-2, M-14 | T-1, T-5, T-8 |

## Связанные документы
- [DFD Documentation](./dfd/README.md)
- [NFR Requirements](./README-nfr.md)
- [Security Policy](../SECURITY.md)
