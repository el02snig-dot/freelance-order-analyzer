from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup

router = Router()

START_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📋 Новый заказ")]],
    resize_keyboard=True,
    input_field_placeholder="Вставь текст заказа...",
)


@router.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer(
        "Привет! Я анализирую фриланс-заказы для команды Zerocoder.\n\n"
        "Пришли текст заказа — покажу:\n"
        "• стек и какие курсы справятся\n"
        "• процент соответствия скиллсету\n"
        "• готовый отклик\n"
        "• оформление для базы или ТГ-канала\n\n"
        "Просто вставь текст заказа 👇",
        reply_markup=START_KEYBOARD,
    )


@router.message(Command("help"))
async def help_cmd(message: Message) -> None:
    await message.answer(
        "Пришли текст фриланс-заказа (или ссылку) — я разберу его по действиям.\n\n"
        "Можно прислать новый заказ в любой момент.\n\n"
        "/cancel — отменить текущее действие и вернуться в начало.",
        reply_markup=START_KEYBOARD,
    )


@router.message(Command("cancel"))
async def cancel_cmd(message: Message, state: FSMContext) -> None:
    current = await state.get_state()
    await state.clear()
    if current:
        await message.answer("Действие отменено. Пришли текст нового заказа 👇", reply_markup=START_KEYBOARD)
    else:
        await message.answer("Нечего отменять. Просто пришли текст заказа 👇", reply_markup=START_KEYBOARD)
