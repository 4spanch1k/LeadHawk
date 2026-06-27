# LeadHawk

LeadHawk is a Python tool for discovering fresh freelance leads from public
Telegram sources using Google Custom Search and Telethon.

It helps find public requests for websites, landing pages, Telegram bots, mini
apps, CRM integrations, parsers, and frontend tasks.

LeadHawk ищет свежие публичные заявки на сайты, лендинги, Telegram-ботов,
Mini Apps, CRM, парсеры, интеграции и frontend-задачи. Он обнаруживает
публичные `t.me`-источники через Google Custom Search API, читает их через
Telethon, фильтрует заявки, оценивает качество и экспортирует результат в CSV.

Проект не читает приватные чаты, не обходит капчи или ограничения платформ и
не отправляет сообщения потенциальным клиентам.

## Security

Do not commit `.env`, Telegram session files, logs, SQLite databases, or
exported lead CSV files.

LeadHawk works only with public Telegram sources and does not bypass private
chats, captchas, authentication restrictions, or platform limits.

## Требования

- Python 3.11 или новее
- Telegram-аккаунт и API credentials
- Google Programmable Search Engine с Custom Search JSON API

## Установка

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Папки `data/`, `logs/` и `sessions/` создаются автоматически.

## Настройка Telegram

1. Откройте [my.telegram.org](https://my.telegram.org).
2. Войдите по номеру телефона.
3. Создайте приложение в разделе **API development tools**.
4. Перенесите `api_id` и `api_hash` в `.env`.
5. Укажите телефон в международном формате в `TG_PHONE`.

При первом запуске `parse` Telethon запросит код подтверждения. Сессия
сохранится локально в `sessions/` и исключена из Git.

## Настройка Google

1. Создайте проект в [Google Cloud Console](https://console.cloud.google.com/).
2. Включите **Custom Search JSON API** и создайте API key.
3. Создайте Programmable Search Engine на
   [programmablesearchengine.google.com](https://programmablesearchengine.google.com/).
4. Разрешите поиск по всему интернету либо настройте область поиска на `t.me`.
5. Запишите API key в `GOOGLE_API_KEY`, а идентификатор поисковой системы — в
   `GOOGLE_CX`.

Google API имеет дневные квоты. LeadHawk использует паузы между запросами и не
применяет Selenium или браузерный скрапинг.

## Переменные окружения

```dotenv
TG_API_ID=123456
TG_API_HASH=your_api_hash
TG_PHONE=+77000000000
GOOGLE_API_KEY=your_google_api_key
GOOGLE_CX=your_google_cx
DATABASE_PATH=data/leadhawk.db
HOURS_LOOKBACK=24
MAX_MESSAGES_PER_SOURCE=300
GOOGLE_PAGES_PER_QUERY=2
REQUEST_DELAY_SECONDS=2
```

Увеличение лимитов повышает нагрузку и риск `FloodWait`. Начинайте со значений
по умолчанию.

## Команды

```bash
# Найти новые публичные Telegram-источники через Google
python main.py discover

# Прочитать свежие сообщения из сохранённых источников
python main.py parse

# Создать data/leads.csv
python main.py export

# Выполнить discover → parse → export
python main.py run

# Показать статистику, в том числе на пустой базе
python main.py stats
```

CSV можно открыть в Excel, Numbers, LibreOffice Calc или импортировать в
Google Sheets. Файл записывается с UTF-8 BOM для корректной кириллицы.

## Как работает обработка

1. `google_finder.py` извлекает usernames только из публичных `t.me`-ссылок.
2. `telegram_parser.py` читает ограниченное число свежих сообщений.
3. `lead_filter.py` отсекает найм в штат и пропускает проектные задачи.
4. `lead_extractor.py` выделяет категорию, бюджет, контакты и телефон.
5. `scoring.py` присваивает оценку от 0 до 100.
6. `db.py` предотвращает дубли по источнику и ID сообщения либо хешу текста.

Внешние источники изолированы от конвейера обработки. Для нового способа
добычи достаточно преобразовать найденную запись в `models.PublicMessage`,
после чего используются те же фильтр, extractor, scoring и БД.

## Ограничения и безопасность

- Используются только публичные источники.
- Код не вступает в приватные группы и не обходит авторизацию.
- Недоступные публичные источники помечаются `unavailable`.
- `FloodWait` обрабатывается паузой; между источниками действует rate limit.
- Google и Telegram могут менять квоты и ограничения.
- Телефон, ключи, сессии и база не должны публиковаться в Git.
- Перед сбором и использованием данных соблюдайте правила платформ и
  применимое законодательство.

## Проверка

```bash
pip install -r requirements-dev.txt
pytest
python main.py stats
python main.py export
```
