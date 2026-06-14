# Скилл: Бот для анализа фриланс-заказов

Этот скилл помогает Claude Code работать с репозиторием Telegram-бота для анализа фриланс-заказов.

## Что делает проект

Telegram-бот принимает текст фриланс-заказа и выполняет одно из пяти действий:
1. Определяет стек технологий и подбирает подходящие курсы Zerocoder
2. Проверяет соответствие заказа скиллсету команды
3. Генерирует текст отклика для заказчика
4. Оформляет заказ для внутренней базы
5. Готовит пост для Telegram-канала с баннером

## Структура репозитория

```
analyz_agent/
├── bot/main.py             ← точка входа, запускать через: py -3.11 -m bot.main
├── bot/config.py           ← настройки из .env (токены, модель, разрешённые пользователи)
├── bot/handlers/           ← три хэндлера: common.py, order.py, actions.py
├── bot/keyboards/          ← инлайн-клавиатуры для меню действий
├── bot/states/             ← FSM-состояния (ожидание заказа, выбор действия)
├── ai/analyzer.py          ← оркестратор: принимает заказ, вызывает нужный промпт
├── ai/client.py            ← клиент Anthropic API
├── ai/prompts/             ← промпты для каждого из 5 действий
├── ai/agents/researcher.py ← агент для исследования (ddgs + Claude)
├── services/banner_service.py    ← подбор баннера по типу поста и площадке
├── services/history_service.py   ← сохранение истории заказов в SQLite
├── services/order_processor.py   ← главный обработчик, связывает хэндлеры и AI
├── utils/skillset_loader.py      ← загружает скиллсет курсов из Excel
├── utils/text.py                 ← форматирование и обрезка текста
├── utils/url_fetcher.py          ← получение текста заказа по URL (httpx)
├── banners/                      ← изображения баннеров (frilans, pesochnica, zakazyi...)
├── .env                          ← секреты (не коммитить)
├── .env.example                  ← шаблон конфигурации
└── requirements.txt
```

## Как запустить

```bash
# 1. Установить зависимости
pip install -r requirements.txt

# 2. Создать .env из шаблона и заполнить токены
cp .env.example .env

# 3. Запустить бота
py -3.11 -m bot.main
```

## Как вносить изменения

**Добавить новое действие в меню:**
1. Создать промпт в `ai/prompts/`
2. Добавить вызов в `ai/analyzer.py`
3. Добавить кнопку в `bot/keyboards/`
4. Добавить обработчик в `bot/handlers/actions.py`

**Изменить промпт:**
Файлы в `ai/prompts/` — обычный Python с f-строками. Изменять текст промпта, не трогая структуру функции.

**Добавить новый тип баннера:**
Добавить папку в `banners/` и зарегистрировать путь в `services/banner_service.py`.

**Изменить модель Claude:**
В `.env` изменить `ANTHROPIC_MODEL=claude-opus-4-7` (или другую модель).

## Как проверить ошибки

```bash
# Смотреть логи в реальном времени (структурированный вывод в консоль)
py -3.11 -m bot.main

# Или проверить bot.log
cat bot.log | tail -50
```

Частые ошибки:
- `ValidationError` — не заполнен `.env` или неверный формат токена
- `TelegramUnauthorizedError` — неверный `TELEGRAM_BOT_TOKEN`
- `AuthenticationStatusError` — неверный `ANTHROPIC_API_KEY`
- `sqlite3.OperationalError` — проблема с правами на запись в директорию

## Зависимости

- Python 3.11+
- aiogram >= 3.13
- anthropic >= 0.40
- aiosqlite >= 0.20
- pydantic-settings >= 2.5
- structlog >= 24.4
- httpx >= 0.27
- ddgs >= 6.0
- tenacity >= 8.0
