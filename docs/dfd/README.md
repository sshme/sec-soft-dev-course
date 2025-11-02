# Data Flow Diagrams (DFD) с границами доверия

Документация содержит 4 уровня DFD для Reading Highlights API с детальным анализом границ доверия и мер безопасности.

## Структура документации

### [DFD Level 0: Context Diagram](./DFD-0-context.md)
**Контекстная диаграмма** — высокоуровневый обзор системы и внешних сущностей.

**Основные компоненты:**
- Untrusted Zone (Internet)
- DMZ - API Application
- Internal Zone (S3, Secret Manager)

**Границы доверия:**
- TB-1: Internet → DMZ (HTTPS, JWT, Rate Limiting)
- TB-2: DMZ → Internal Zone (IAM, TLS, Encryption)

**Ключевые потоки данных:**
- DF-1: User credentials
- DF-2: JWT tokens
- DF-3: Highlight CRUD operations
- DF-4: File uploads to S3
- DF-5: Secret retrieval
- DF-6: RFC 7807 error responses

---

### [DFD Level 1: Application Decomposition](./DFD-1-application.md)
**Декомпозиция приложения** на основные компоненты с внутренними границами доверия.

**Слои:**
1. **API Gateway Layer:** Load Balancer, Middleware
2. **Application Layer:** Auth Service, Highlights API, Upload Service
3. **Security Layer:** JWT Verifier, Authorization, Error Handler
4. **Data Layer:** In-Memory Storage, Token Denylist

**Границы доверия:**
- TB-1: Internet → API Gateway (TLS, CORS, Rate Limiting)
- TB-1.1: Gateway → Application (Correlation ID, Input Validation)
- TB-1.2: Application → Security (RBAC, Owner-based Access)
- TB-2: DMZ → Internal Zone (IAM, Encryption)

**Процессы:**
- P-1: Auth Service (JWT issuance)
- P-2: Highlights API (CRUD with ownership)
- P-3: Upload Service (File validation)
- P-4: JWT Verifier (Token validation)
- P-5: Authorization (RBAC + ownership checks)

**Анализ поверхности атак:**
- Entry points (login, token refresh, highlights CRUD, upload)
- Applied mitigations (rate limiting, JWT verification, owner filtering)

---

### [DFD Level 2: Authentication Flow](./DFD-2-authentication.md)
**Детальная декомпозиция аутентификации** с акцентом на JWT и безопасность токенов.

**Компоненты:**
1. **Entry Point:** Rate Limiter (5 req/min), Correlation ID Generator
2. **Auth Endpoints:** Login, Token Refresh, Logout
3. **Authentication Logic:** Credential Validator, Token Issuer/Verifier
4. **Security Components:** JWT Encoder/Decoder, Clock Skew Handler, Denylist

**Границы доверия:**
- TB-1: Untrusted → Rate Limiter (DDoS protection)
- TB-1.1: Rate Limiter → Auth Endpoints (Input validation)
- TB-1.2: Endpoints → Auth Logic (Stateless, no enumeration)
- TB-1.3: Logic → Security Components (HS256, dual-key rotation)
- TB-2: DMZ → Secret Manager (TLS, audit logging)

**Процессы:**
- P-1: Login Flow (credentials → tokens)
- P-2: Token Refresh Flow (refresh → new tokens + denylist old)
- P-3: Logout Flow (revoke refresh token)

**Сценарии атак:**
- AS-1: Credential Stuffing (→ rate limiting)
- AS-2: Token Replay (→ short TTL, HTTPS)
- AS-3: JWT Algorithm Confusion (→ hardcoded HS256)
- AS-4: Clock Skew Exploitation (→ server-side clock only)
- AS-5: Secret Key Compromise (→ dual-key rotation)

**Security Controls Matrix:**
| Control | Login | Refresh | Logout |
|---------|-------|---------|--------|
| Rate Limiting |  5/min |  5/min | x |
| JWT Signature |  Issue |  Verify |  Verify |
| Denylist | x |  Check |  Add |

---

### [DFD Level 3: File Upload Flow](./DFD-3-file-upload.md)
**Детальная декомпозиция загрузки файлов** с многоуровневой валидацией.

**Этапы валидации:**
1. **Entry Validation (TB-1.1):**
   - JWT authentication
   - Rate limiting (3 uploads/min per user)
   - Size check (≤ 5MB)

2. **File Validation (TB-1.2):**
   - MIME type check (Content-Type header)
   - Magic bytes validation (PNG: 8 bytes, JPEG: start+end)
   - Type matching (MIME vs signature)

3. **Path Security (TB-1.3):**
   - UUID v4 filename generation
   - Path canonicalization (`Path.resolve(strict=True)`)
   - Symlink detection in parent chain
   - Traversal prevention (prefix validation)

4. **Temporary Storage (TB-1.4):**
   - Write to TMP_DIR only
   - Re-verify magic bytes after write
   - Atomic operations

5. **S3 Upload (TB-2.1):**
   - TLS connection to S3
   - Server-side encryption (AES256)
   - UUID object keys
   - Metadata (user_sub, correlation_id, size)

6. **Cleanup:**
   - Delete temp file after S3 upload
   - Periodic cleanup of old files

**Границы доверия:**
- TB-1: Untrusted → Entry (Auth + Rate Limit + Size)
- TB-1.1: Entry → File Validation (Magic bytes + MIME)
- TB-1.2: File → Path Security (UUID + Canonicalization)
- TB-1.3: Path → Temp Storage (Restricted permissions)
- TB-1.4: Temp → S3 (TLS + IAM + Encryption)
- TB-2: DMZ → S3 (IAM role, bucket policy)

**Сценарии атак:**
- AS-1: Polyglot File (→ magic bytes + no execution)
- AS-2: Path Traversal (→ UUID generation + canonicalization)
- AS-3: Symlink Attack (→ parent chain check)
- AS-4: Magic Bytes Spoofing (→ full validation)
- AS-5: ZIP Bomb (→ no decompression + size limit)
- AS-6: XXE via SVG (→ SVG not allowed)

**Step-by-Step Validation Table:**
| Step | Component | Validation | Failure |
|------|-----------|------------|---------|
| 1 | AuthCheck | JWT signature | 401 Unauthorized |
| 2 | RateLimiter | 3/min per user | 429 Too Many Requests |
| 3 | SizeCheck | ≤ 5MB | 413 Payload Too Large |
| 4 | MagicBytes | PNG/JPEG signature | 400 Invalid Signature |
| 5 | PathCanon | Prefix in TMP_DIR | 403 Traversal Detected |
| 6 | SymlinkCheck | No symlinks | 403 Symlink Detected |
| 7 | S3Client | Upload with AES256 | 500 Upload Failed |

---

## Общие принципы безопасности

### Defense in Depth
Каждая граница доверия защищена несколькими уровнями контролей:
- **Network:** HTTPS/TLS, network segmentation
- **Application:** JWT authentication, input validation
- **Data:** Encryption at rest and in transit
- **Audit:** Comprehensive logging with correlation IDs

### Trust Zones
```
Untrusted (Internet)
    ↓ TB-1: TLS + Auth + Rate Limit
DMZ (API Application)
    ↓ TB-2: IAM + Encryption + Audit
Internal (S3, Secrets)
```

### Security Controls Matrix

| Zone | Authentication | Authorization | Encryption | Audit | Rate Limiting |
|------|----------------|---------------|------------|-------|---------------|
| Untrusted | x | x | HTTPS | x | Client-side |
| DMZ |  JWT |  RBAC | HTTPS |  Correlation ID |  Per IP/User |
| Internal |  IAM |  Bucket Policy | TLS + AES256 |  S3 Access Logs | x |

### Compliance Mapping

| NFR | DFD Reference | Implementation |
|-----|---------------|----------------|
| NFR-01 | DFD-0, DFD-1 | RFC 7807 error format with correlation_id |
| NFR-02 | DFD-1, DFD-2 | Correlation ID middleware, masked secrets |
| NFR-03 | DFD-1 | Pydantic validation (text ≤ 2000, tags ≤ 10) |
| NFR-04 | DFD-3 | Magic bytes validation, S3 encryption, UUID keys |
| NFR-05 | DFD-2 | SECRET_KEY + SECRET_KEY_PREV rotation |
| NFR-06 | DFD-2 | JWT HS256, 15min/7day TTL, clock skew ±60s |
| NFR-07 | DFD-1 | RBAC + ownership, owner_id filtering |
| NFR-08 | DFD-0, DFD-1 | Rate limiting (10/min highlights, 5/min auth) |

---

## Использование документации

### Для разработчиков
1. Изучите DFD-1 для понимания архитектуры
2. Используйте DFD-2/DFD-3 для имплементации новых функций
3. Следуйте паттернам границ доверия при добавлении кода

### Для аудиторов безопасности
1. Начните с DFD-0 для понимания контекста
2. Проверьте реализацию контролей из таблиц Security Controls
3. Верифицируйте сценарии атак (AS-1, AS-2, etc.)

### Для архитекторов
1. DFD-0 — для обсуждения с бизнесом
2. DFD-1 — для технических дизайн-ревью
3. DFD-2/3 — для углубленного анализа критических компонентов

---

## Связанные документы

- [NFR Requirements](../README-nfr.md)
- [ADR-001: RFC 7807 Error Format](../adr/ADR-001-rfc7807-error-format.md)
- [ADR-002: Input Validation & File Uploads](../adr/ADR-002-input-validation-file-uploads.md)
- [ADR-003: Secrets Management](../adr/ADR-003-secrets-management.md)
- [ADR-004: Authentication (JWT)](../adr/ADR-004-authentication.md)
- [ADR-005: Authorization (RBAC + Ownership)](../adr/ADR-005-authorization.md)
- [API Documentation](../API.md)

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-02 | Initial DFD documentation with 4 levels |
