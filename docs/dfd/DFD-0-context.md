# DFD Level 0: Context Diagram

Контекстная диаграмма показывает систему как единое целое и её взаимодействие с внешними сущностями.

```mermaid
graph TB
    subgraph "Untrusted Zone"
        User[User/Browser]
        Admin[Admin User]
        Attacker[Potential Attacker]
    end

    subgraph "DMZ - Trust Boundary 1"
        API[Reading Highlights API<br/>FastAPI Application]
    end

    subgraph "Internal Zone - Trust Boundary 2"
        S3[(S3 Storage<br/>File Uploads)]
        SecretMgr[Secret Manager<br/>AWS/Vault]
    end

    User -->|HTTPS Requests<br/>JWT Bearer Token| API
    Admin -->|HTTPS Requests<br/>Admin Credentials| API
    Attacker -.->|Attack Attempts<br/>Invalid Tokens| API

    API -->|Store/Retrieve Files<br/>Server-Side Encryption| S3
    API -->|Fetch Secrets<br/>TLS Connection| SecretMgr

    API -->|RFC 7807 Errors<br/>Correlation ID| User
    API -->|Admin Operations<br/>Audit Logs| Admin

    classDef untrusted fill:#ff9999,stroke:#ff0000,stroke-width:2px
    classDef dmz fill:#ffeb99,stroke:#ff8800,stroke-width:2px
    classDef internal fill:#99ff99,stroke:#00aa00,stroke-width:2px

    class User,Admin,Attacker untrusted
    class API dmz
    class S3,SecretMgr internal
```

## Границы доверия

### TB-1: Internet → DMZ
- **Защита:** HTTPS/TLS, аутентификация JWT, ограничение частоты запросов
- **Угрозы:** MITM, повторные атаки, перебор учетных данных, DDoS
- **Контроли:**
  - Проверка подписи JWT (HS256)
  - Ограничение запросов (10 req/min для highlights, 5 req/min для auth)
  - Валидация ввода (схемы Pydantic)
  - Политики CORS

### TB-2: DMZ → Internal Zone
- **Защита:** Аутентификация сервисов, роли IAM, шифрование
- **Угрозы:** Боковое перемещение, утечка данных, повышение привилегий
- **Контроли:**
  - Серверное шифрование S3 (AES256)
  - Доступ на основе ролей IAM
  - TLS-соединения с Secret Manager
  - Сегментация сети

## Потоки данных

| Поток | Источник | Назначение | Данные | Безопасность |
|-------|----------|------------|--------|---------------|
| DF-1 | Пользователь | API | Учетные данные (username/password) | HTTPS, ограничение запросов |
| DF-2 | API | Пользователь | JWT токены (access + refresh) | HTTPS, HttpOnly cookies |
| DF-3 | Пользователь | API | CRUD операции с highlights | HTTPS, JWT Bearer auth |
| DF-4 | API | S3 | Загрузка файлов (изображения) | TLS, шифрование AES256 |
| DF-5 | API | Secret Manager | Получение секретов | TLS, IAM auth |
| DF-6 | API | Пользователь | Ошибки RFC 7807 | HTTPS, скрытые детали |

## Контроли безопасности по зонам

### Недоверенная зона (Untrusted Zone)
- Отсутствие предположений о доверии
- Весь ввод считается враждебным
- Валидация на стороне клиента опциональна

### DMZ (уровень API)
- Валидация JWT при каждом запросе
- Проверки авторизации на основе владельца
- Отслеживание Correlation ID
- Структурированное логирование (секреты скрыты)
- Ограничение запросов по IP/пользователю

### Внутренняя зона (Internal Zone)
- Шифрование в покое (S3)
- Шифрование при передаче (TLS)
- Доступ только через служебные учетные записи
- Включено аудит-логирование
