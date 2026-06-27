from __future__ import annotations

GOOGLE_SEARCH_URL = "https://www.googleapis.com/customsearch/v1"

GOOGLE_QUERIES = (
    'site:t.me "нужен сайт" "бюджет" -вакансия -резюме',
    'site:t.me "сделать сайт" "оплата" -вакансия',
    'site:t.me "нужен лендинг" -вакансия',
    'site:t.me "нужен телеграм бот" -вакансия',
    'site:t.me "telegram bot" "budget"',
    'site:t.me "telegram mini app" "бюджет"',
    'site:t.me "mini app" "оплата"',
    'site:t.me "нужен парсер" "бюджет"',
    'site:t.me "нужен скрапер" "оплата"',
    'site:t.me "интеграция amoCRM"',
    'site:t.me "сделать CRM"',
    'site:t.me "ищу разработчика" "лендинг" -full-time',
    'site:t.me "ищу frontend" "проект" -вакансия',
    'site:t.me "нужна верстка" "бюджет"',
)

GOOD_KEYWORDS = (
    "нужен сайт", "сделать сайт", "создать сайт", "разработать сайт",
    "сайт под ключ", "лендинг", "landing page", "нужен лендинг",
    "telegram bot", "телеграм бот", "бот в телеграм", "тг бот", "tg bot",
    "mini app", "мини апп", "telegram mini app", "парсер", "скрапер",
    "scraping", "parser", "crm", "amocrm", "amo crm", "bitrix", "битрикс",
    "интеграция", "api интеграция", "frontend", "фронтенд", "верстка",
    "вёрстка", "сверстать", "web app", "веб приложение",
)

JOB_KEYWORDS = (
    "вакансия", "ищем сотрудника", "ищем разработчика в команду", "зарплата",
    "оклад", "ставка в месяц", "full-time", "part-time", "офис", "стажировка",
    "резюме", " hr ", "рекрутер", "постоянная работа", "на постоянку",
    "ищем в штат", "требуется сотрудник", "senior", "middle",
    "junior в команду",
)

PROJECT_SIGNALS = (
    "нужно сделать", "проект", "разовая задача", "бюджет",
    "оплата за проект", "ищу исполнителя", "сделать",
)

HIGH_VALUE_CATEGORIES = {
    "website", "telegram_bot", "mini_app", "parser", "crm", "frontend",
}

SOURCE_ACTIVE = "active"
SOURCE_NEW = "new"
SOURCE_UNAVAILABLE = "unavailable"

