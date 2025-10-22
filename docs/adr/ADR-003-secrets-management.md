# ADR-003: Secrets Management

Дата: 2025-10-22
Статус: Accepted

## Context

Приложение требует конфиденциальной конфигурации:
- Database connection strings (если используется БД)
- API ключи для внешних сервисов (если интегрируется с сторонними API)
- JWT signing secrets (для аутентификации)
- Encryption keys для sensitive данных

Риски при неправильном управлении секретами:
- **Hardcoded secrets:** Секреты в коде → утечка через Git history
- **Логирование:** Случайное логирование секретов в plain text
- **Environment exposure:** `.env` файлы в продакшне без должной защиты
- **No rotation:** Компрометированный секрет невозможно обновить без redeploy

Требования:
- NFR-05: Ротация секретов без простоя
- Compliance: Секреты не должны храниться в VCS
- Auditability: Отслеживание использования секретов

## Decision

Внедряем иерархическую систему управления секретами:

### 1. Источники секретов (по приоритету):

**Development (локальная разработка):**
```python
# .env (не коммитится в Git)
DATABASE_URL=sqlite:///dev.db
SECRET_KEY=dev-secret-123
```

**Production:**
```python
# Переменные окружения из container orchestrator
# или Secret Manager (AWS Secrets Manager, HashiCorp Vault, etc.)
DATABASE_URL=${SECRETS_MANAGER_DB_URL}
SECRET_KEY=${SECRETS_MANAGER_SECRET_KEY}
```

### 2. Правила доступа:
- **ЗАПРЕЩЕНО:** Hardcode в коде, коммит в Git, print/log в plain text
- **РАЗРЕШЕНО:** Чтение из env vars, использование secrets управляющих систем
- **Обязательно:** Валидация наличия обязательных секретов при старте

### 3. Реализация (`app/config.py`):
```python
import os
from typing import Optional

class Config:
    def __init__(self):
        self.database_url = self._get_secret("DATABASE_URL", required=False)
        self.secret_key = self._get_secret("SECRET_KEY", required=True)
        # Маскируем секреты в repr

    def _get_secret(self, key: str, required: bool = True) -> Optional[str]:
        value = os.getenv(key)
        if required and not value:
            raise ValueError(f"Required secret {key} not found")
        return value

    def __repr__(self):
        return f"Config(database_url='***', secret_key='***')"
```

### 4. Ротация секретов:
- **Graceful degradation:** Приложение поддерживает 2 версии секрета одновременно (current + previous)
- **Zero-downtime rotation:**
  1. Добавить новый секрет как `SECRET_KEY_NEW`
  2. Deploy код с поддержкой обоих ключей
  3. Обновить `SECRET_KEY` на новое значение
  4. Удалить `SECRET_KEY_NEW`
- **Автоматизация:** Скрипт для ротации через CI/CD

### 5. Логирование:
- **Sanitization:** Автоматически маскировать секреты в логах
- **Pattern matching:** Regex для обнаружения потенциальных секретов (длинные hex/base64 строки)
- **Structured logging:** JSON формат с явным полем `sensitive: true` для исключения из сбора

### 6. Валидация при старте:
```python
@app.on_event("startup")
def validate_config():
    config = Config()
    if not config.secret_key:
        raise RuntimeError("SECRET_KEY not configured")
```

## Consequences

### Плюсы:
- **Security:** Секреты не попадают в VCS
- **Auditability:** Secret manager логирует все обращения
- **Rotation:** Возможность обновления без простоя
- **Environment parity:** Единый механизм для dev/staging/prod
- **Compliance:** Соответствие SOC2, ISO 27001

### Минусы:
- **Complexity:** Требует настройки Secret Manager в продакшне
- **Dependency:** Отказ Secret Manager → невозможность старта новых инстансов
- **Latency:** Обращение к внешнему Secret Manager +10-50ms при старте
- **Cost:** AWS Secrets Manager ~$0.40/secret/month + $0.05/10k requests

### Влияние:
- **DX:** Упрощается (разработчики используют `.env`, ops — Secret Manager)
- **Deployment:** Требует интеграции с Secret Manager в CI/CD
- **Incident response:** При компрометации секрета достаточно ротации, не нужен redeploy

### Альтернативы отклонены:
- **Encrypted secrets в Git (SOPS, git-crypt):** Сложность управления ключами шифрования
- **Config files в container image:** Секреты в Docker layers → риск утечки
- **Hardcoded rotation schedule:** Негибкость, риск пропуска ротации

## Links

- [12-Factor App: Config](https://12factor.net/config)
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- NFR-05 (Secrets Rotation)
- `app/config.py` - реализация конфигурации
- `tests/test_config.py::test_missing_required_secret` - тесты валидации
- `.env.example` - шаблон для локальной разработки
