from __future__ import annotations

import structlog
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.config import settings
from bot.keyboards.actions import actions_keyboard
from bot.states.order import OrderState
from utils.url_fetcher import fetch_order_text

logger = structlog.get_logger()
router = Router()


@router.message()
async def receive_order(message: Message, state: FSMContext) -> None:
    if not message.text:
        return

    text = message.text.strip()

    if text == "📋 Новый заказ":
        await message.answer("Вставь текст заказа — я разберу его 👇")
        return

    if text.startswith(("http://", "https://")):
        thinking = await message.answer("⏳ Загружаю страницу...")
        try:
            text = await fetch_order_text(text)
        except Exception as e:
            logger.error("url_fetch_failed", url=message.text[:100], error=str(e))
            await thinking.edit_text(
                f"❌ Не удалось загрузить страницу.\n{e}\n\n"
                "Попробуй скопировать текст заказа вручную."
            )
            return
        await thinking.delete()

    if len(text) > settings.max_order_length:
        await message.answer(
            f"Текст слишком длинный — максимум {settings.max_order_length} символов. "
            "Сократи и попробуй снова."
        )
        return

    # set_data (not update_data) чтобы сбросить кэш предыдущего заказа
    await state.set_data({"order_text": text})
    await state.set_state(OrderState.waiting_for_action)

    logger.info("order_received", user_id=message.from_user.id, length=len(text))

    await message.answer("Заказ получен. Что сделать?", reply_markup=actions_keyboard())
