# ADR-002: Input Validation and File Uploads

Дата: 2025-10-22
Статус: Accepted

## Context

Приложение принимает пользовательский ввод (highlights, источники, теги) и потенциально может поддерживать загрузку файлов (например, скриншоты highlights, обложки книг). Существуют риски:

- **Path Traversal:** Загрузка файлов с именами типа `../../etc/passwd`
- **Magic Bytes Spoofing:** Файл с расширением `.jpg` содержит исполняемый код
- **DoS через размер:** Загрузка файлов >100MB может исчерпать память/диск
- **Symlink Attacks:** Запись по симлинку на системные файлы
- **MIME Type Confusion:** Клиент отправляет неверный `Content-Type`

Без проверок на уровне приложения возможны:
- Выполнение произвольного кода (RCE)
- Утечка файловой системы
- DoS-атаки
- XSS через SVG/HTML файлы

## Decision

Внедряем многоуровневую валидацию для всех входных данных:

### 1. Текстовые поля (highlights/source/tags):
- **Длина:** `text` ≤ 2000 chars, `source` ≤ 500 chars (уже реализовано в Pydantic)
- **Теги:** max 10 тегов, lowercase, trimmed
- **Санитизация:** Strip HTML/script tags если формат не требует разметки

### 2. Загрузка файлов (если реализовано):
- **Размер:** MAX_UPLOAD_SIZE = 5 MB (5_000_000 bytes)
- **Magic Bytes Validation:**
  - PNG: `\x89PNG\r\n\x1a\n` (первые 8 байт)
  - JPEG: `\xff\xd8` (начало) + `\xff\xd9` (конец)
  - Отклонять файлы с несоответствием magic bytes и расширения
- **Whitelist типов:** `image/png`, `image/jpeg` только
- **Имя файла:** Генерировать UUID, игнорировать клиентское имя
- **Path Canonicalization:**
  ```python
  root = Path(UPLOAD_DIR).resolve(strict=True)
  target = (root / f"{uuid4()}.ext").resolve()
  if not str(target).startswith(str(root)):
      raise SecurityError("path_traversal")
  ```
- **Symlink Prevention:** Проверять `path.is_symlink()` для всех родительских директорий
- **Timeout:** Загрузка должна завершиться за 30 сек

### 3. Параметры запроса:
- Использовать `Query()` с явными constraints
- Валидировать перечисления (enums) для filter параметров

### 4. Rate Limiting (вне скоупа ADR, но relevant):
- Endpoint `/highlights` (POST): 10 req/min per IP
- Upload endpoint: 3 req/min per authenticated user

## Consequences

### Плюсы:
- **Безопасность:** Предотвращение Path Traversal, RCE, DoS
- **Integrity:** Гарантия соответствия типа содержимому файла
- **Predictability:** UUID имена предотвращают конфликты
- **Defense in Depth:** Несколько слоев проверок (magic bytes + extension + size)

### Минусы:
- **UX:** Пользователи не видят оригинальные имена файлов (нужно хранить metadata)
- **Performance:** Magic bytes validation требует чтения первых N байт файла
- **Complexity:** Требует ручной реализации (библиотеки типа `python-magic` имеют зависимости)

### Влияние:
- **Latency:** +2-5ms на файл для validation
- **Storage:** UUID имена → невозможность дедупликации по имени (нужен hash-based approach)
- **Compliance:** Соответствует OWASP Top 10 (A01:2021 - Broken Access Control)

### Альтернативы отклонены:
- **Доверие MIME от клиента:** Легко подделывается
- **Regex на расширение:** Не защищает от polyglot files
- **`python-magic` (libmagic):** Требует системную зависимость, излишне для 2 типов

## Links

- [OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html)
- NFR-01 (Input Validation)
- F1 из Threat Model (Path Traversal)
- R2 из Threat Model (Magic Bytes Spoofing)
- `app/upload.py` - реализация secure file upload
- `tests/test_upload.py::test_rejects_*` - негативные тесты
