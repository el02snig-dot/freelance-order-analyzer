from __future__ import annotations

LEVEL_LABELS = {
    "junior": "Джун",
    "middle": "Миддл",
    "senior": "Сеньор",
}

# Рыночные ставки СНГ IT-рынок (фриланс, 2024-2025)
_RATES = {
    "junior": {
        "rate_usd": "8–15 $/ч",
        "rate_rub": "700–1 400 ₽/ч",
        "monthly_usd": "$600–1 200/мес",
        "monthly_rub": "55 000–110 000 ₽/мес",
    },
    "middle": {
        "rate_usd": "20–40 $/ч",
        "rate_rub": "1 800–3 700 ₽/ч",
        "monthly_usd": "$2 000–4 000/мес",
        "monthly_rub": "180 000–370 000 ₽/мес",
    },
    "senior": {
        "rate_usd": "50–80 $/ч",
        "rate_rub": "4 600–7 400 ₽/ч",
        "monthly_usd": "$5 000–8 000/мес",
        "monthly_rub": "460 000–740 000 ₽/мес",
    },
}


def system(level: str) -> str:
    rates = _RATES.get(level, _RATES["middle"])
    label = LEVEL_LABELS.get(level, level)
    return f"""\
Ты — эксперт по фриланс-рынку СНГ. Отвечай ТОЛЬКО в формате ниже, без единого лишнего слова.

Уровень: {label}
Ставка: {rates["rate_usd"]} / {rates["rate_rub"]}

ЗАПРЕЩЕНО добавлять любые блоки кроме трёх указанных: сроки+стоимость, риски, совет.
НЕ пиши "Из чего складывается", "Этапы", "Итого часов" и любые другие разделы.

ФОРМАТ (строго, без отклонений):

👤 {label} | ⏱ [X]–[Y] дней | 💰 $[min]–$[max] / [min]–[max] ₽

⚠️ Риски: [риск 1], [риск 2]

💡 [Один совет для {label}а]\
"""


def user(order_text: str) -> str:
    return f"Заказ:\n{order_text}"
