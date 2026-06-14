from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class OrderState(StatesGroup):
    waiting_for_action = State()
    waiting_for_otklik_type = State()
    waiting_for_baza_action = State()
    waiting_for_tg_channel = State()
    waiting_for_tg_pesochnica_type = State()
    waiting_for_tg_subchannel = State()
    waiting_for_tg_birzha_category = State()
    waiting_for_baza_rename = State()
    waiting_for_baza_custom_title = State()
    waiting_for_estimate_level = State()
    waiting_for_banner_pick = State()
    waiting_for_tg_edit = State()
