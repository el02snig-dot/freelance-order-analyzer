from __future__ import annotations

from enum import Enum

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class Action(str, Enum):
    STEK = "stek"
    SOOTVETSTVIE = "sootvetstvie"
    OTKLIK = "otklik"
    BAZA = "baza"
    TG = "tg"
    ESTIMATE = "estimate"


ACTION_LABELS: dict[Action, str] = {
    Action.STEK: "1. Кто справится?",
    Action.SOOTVETSTVIE: "2. Можем взять такой заказ?",
    Action.OTKLIK: "3. Написать отклик",
    Action.BAZA: "4. Оформить для базы",
    Action.TG: "5. Оформить для ТГ",
    Action.ESTIMATE: "6. 💰 Оценка заказа",
}


def actions_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for action, label in ACTION_LABELS.items():
        builder.button(text=label, callback_data=f"action:{action.value}")
    builder.button(text="📋 Новый заказ", callback_data="new_order")
    builder.adjust(1)
    return builder.as_markup()


def otklik_type_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="👤 Отклик от разработчика", callback_data="otklik_type:developer")
    builder.button(text="👥 Отклик от команды", callback_data="otklik_type:team")
    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(1)
    return builder.as_markup()


def baza_actions_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Увеличить описание", callback_data="baza:expand")
    builder.button(text="✂️ Сократить описание", callback_data="baza:shorten")
    builder.button(text="✏️ Поменять название", callback_data="baza:rename")
    builder.button(text="🎨 Придумать баннер", callback_data="baza:banner")
    builder.button(text="✅ Готово! Вернуться в меню", callback_data="baza:done")
    builder.adjust(2, 1, 1, 1)
    return builder.as_markup()


def baza_title_keyboard(titles: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for i, title in enumerate(titles):
        builder.button(text=title, callback_data=f"baza_title:{i}")
    builder.button(text="✏️ Ввести своё", callback_data="baza_title:custom")
    builder.button(text="← Назад", callback_data="baza_title:back")
    builder.adjust(1)
    return builder.as_markup()


def tg_channel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="В песочку", callback_data="tg_channel:pesochnica")
    builder.button(text="На фриланс", callback_data="tg_channel:frilans")
    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(2, 1)
    return builder.as_markup()


def tg_pesochnica_type_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Вакансия", callback_data="tg_ptype:pesochnica")
    builder.button(text="Заказ", callback_data="tg_ptype:zakazyi")
    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(2, 1)
    return builder.as_markup()


def tg_pesochnica_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Биржа", callback_data="tg_sub:birzha")
    builder.button(text="Чат", callback_data="tg_sub:chat")
    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(2, 1)
    return builder.as_markup()


def tg_birzha_category_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🌐 Веб / Дизайн", callback_data="tg_bcat:web_design")
    builder.button(text="📱 Мобилка", callback_data="tg_bcat:mobile")
    builder.button(text="🔧 Другое", callback_data="tg_bcat:etc")
    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(2, 1, 1)
    return builder.as_markup()


def banner_pick_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🖼 Сгенерить баннер 1", callback_data="banner_gen:0")
    builder.button(text="🖼 Сгенерить баннер 2", callback_data="banner_gen:1")
    builder.button(text="🖼 Сгенерить баннер 3", callback_data="banner_gen:2")
    builder.button(text="← Назад", callback_data="banner_gen:back")
    builder.adjust(1)
    return builder.as_markup()


def estimate_level_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🌱 Джун", callback_data="estimate_level:junior")
    builder.button(text="⚙️ Миддл", callback_data="estimate_level:middle")
    builder.button(text="🚀 Сеньор", callback_data="estimate_level:senior")
    builder.button(text="← Назад в меню", callback_data="estimate_level:back")
    builder.adjust(3, 1)
    return builder.as_markup()


def tg_edit_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✂️ Сократить описание", callback_data="tg_edit:shorten")
    builder.button(text="📝 Увеличить описание", callback_data="tg_edit:expand")
    builder.button(text="✅ Готово! Вернуться в меню", callback_data="tg_edit:done")
    builder.adjust(2, 1)
    return builder.as_markup()


def tg_frilans_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Питон", callback_data="tg_sub:python")
    builder.button(text="Промпт", callback_data="tg_sub:prompt")
    builder.adjust(2)
    return builder.as_markup()
