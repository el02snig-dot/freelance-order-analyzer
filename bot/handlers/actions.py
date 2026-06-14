from __future__ import annotations

import structlog
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message

from bot.keyboards.actions import (
    Action,
    actions_keyboard,
    baza_actions_keyboard,
    baza_title_keyboard,
    banner_pick_keyboard,
    estimate_level_keyboard,
    otklik_type_keyboard,
    tg_birzha_category_keyboard,
    tg_channel_keyboard,
    tg_edit_keyboard,
    tg_frilans_keyboard,
    tg_pesochnica_keyboard,
    tg_pesochnica_type_keyboard,
)
from bot.states.order import OrderState
from services.banner_service import get_random_banner
from services.history_service import HistoryService
from services.order_processor import OrderProcessor
from utils.text import split_message

logger = structlog.get_logger()
router = Router()


def _strip_hashtag_lines(text: str) -> str:
    lines = text.rstrip().split("\n")
    while lines and all(w.startswith("#") for w in lines[-1].split() if w):
        lines.pop()
    return "\n".join(lines).rstrip()


@router.callback_query(F.data.startswith("action:"), OrderState.waiting_for_action)
async def handle_action(callback: CallbackQuery, state: FSMContext, processor: OrderProcessor) -> None:
    action_value = callback.data.removeprefix("action:")

    try:
        action = Action(action_value)
    except ValueError:
        await callback.answer("Неизвестное действие")
        return

    data = await state.get_data()
    order_text: str = data.get("order_text", "")

    if not order_text:
        await callback.answer("Сначала пришли текст заказа")
        return

    await callback.answer()

    if action == Action.TG:
        await state.set_state(OrderState.waiting_for_tg_channel)
        await callback.message.answer("Куда публикуем?", reply_markup=tg_channel_keyboard())
        return

    if action == Action.ESTIMATE:
        await state.set_state(OrderState.waiting_for_estimate_level)
        await callback.message.answer("Выбери уровень специалиста:", reply_markup=estimate_level_keyboard())
        return

    if action == Action.OTKLIK:
        await state.set_state(OrderState.waiting_for_otklik_type)
        await callback.message.answer("От кого пишем отклик?", reply_markup=otklik_type_keyboard())
        return

    cache_key = f"cache_{action.value}"
    if cached := data.get(cache_key):
        logger.info("action_cache_hit", action=action.value)
        for chunk in split_message(cached):
            await callback.message.answer(chunk)
        if action == Action.BAZA:
            await state.update_data(baza_result=cached)
            await state.set_state(OrderState.waiting_for_baza_action)
            await callback.message.answer("Что сделать с описанием?", reply_markup=baza_actions_keyboard())
        else:
            await callback.message.answer("Что ещё сделать?", reply_markup=actions_keyboard())
        return

    thinking = await callback.message.answer("⏳ Анализирую заказ...")
    logger.info("action_selected", user_id=callback.from_user.id, action=action.value)

    try:
        result = await processor.process(action, order_text)
    except Exception as e:
        logger.error("action_failed", action=action.value, error=str(e))
        await thinking.edit_text("❌ Что-то пошло не так. Попробуй ещё раз.")
        await callback.message.answer("Что ещё сделать?", reply_markup=actions_keyboard())
        return

    await thinking.delete()
    await HistoryService.save(callback.from_user.id, order_text, action.value, result)
    await state.update_data(**{cache_key: result})

    for chunk in split_message(result):
        await callback.message.answer(chunk)

    if action == Action.BAZA:
        await state.update_data(baza_result=result)
        await state.set_state(OrderState.waiting_for_baza_action)
        await callback.message.answer("Что сделать с описанием?", reply_markup=baza_actions_keyboard())
        return

    await callback.message.answer("Что ещё сделать?", reply_markup=actions_keyboard())


@router.callback_query(F.data == "new_order")
async def handle_new_order(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await callback.message.answer("Жду новый заказ — вставь текст 👇")


@router.callback_query(F.data == "cancel")
async def handle_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await callback.message.answer("Отменено. Пришли текст нового заказа 👇")


@router.callback_query(F.data.startswith("otklik_type:"), OrderState.waiting_for_otklik_type)
async def handle_otklik_type(callback: CallbackQuery, state: FSMContext, processor: OrderProcessor) -> None:
    otklik_type = callback.data.removeprefix("otklik_type:")
    await callback.answer()

    data = await state.get_data()
    order_text: str = data.get("order_text", "")

    cache_key = f"cache_otklik_{otklik_type}"
    if cached := data.get(cache_key):
        logger.info("otklik_cache_hit", otklik_type=otklik_type)
        for chunk in split_message(cached):
            await callback.message.answer(chunk)
        await state.set_state(OrderState.waiting_for_action)
        await callback.message.answer("Что ещё сделать?", reply_markup=actions_keyboard())
        return

    thinking = await callback.message.answer("⏳ Пишу отклик...")
    logger.info("action_selected", user_id=callback.from_user.id, action=f"otklik_{otklik_type}")

    try:
        if otklik_type == "developer":
            result = await processor.analyzer.generate_response_developer(order_text)
        else:
            result = await processor.analyzer.generate_response_team(order_text)
    except Exception as e:
        logger.error("otklik_failed", otklik_type=otklik_type, error=str(e))
        await thinking.edit_text("❌ Что-то пошло не так. Попробуй ещё раз.")
        await state.set_state(OrderState.waiting_for_action)
        await callback.message.answer("Что ещё сделать?", reply_markup=actions_keyboard())
        return

    await thinking.delete()
    await HistoryService.save(callback.from_user.id, order_text, f"otklik_{otklik_type}", result)
    await state.update_data(**{cache_key: result})

    for chunk in split_message(result):
        await callback.message.answer(chunk)

    await state.set_state(OrderState.waiting_for_action)
    await callback.message.answer("Что ещё сделать?", reply_markup=actions_keyboard())


@router.callback_query(F.data.startswith("baza:"), OrderState.waiting_for_baza_action)
async def handle_baza_action(callback: CallbackQuery, state: FSMContext, processor: OrderProcessor) -> None:
    action = callback.data.removeprefix("baza:")
    await callback.answer()

    data = await state.get_data()
    current_text: str = data.get("baza_result", "")

    if action == "done":
        await state.set_state(OrderState.waiting_for_action)
        await callback.message.answer("Что ещё сделать?", reply_markup=actions_keyboard())
        return

    if action == "banner":
        thinking = await callback.message.answer("⏳ Придумываю идеи баннера...")
        try:
            result, banner_prompts = await processor.analyzer.suggest_banners(current_text)
        except Exception as e:
            logger.error("baza_banner_failed", error=str(e))
            await thinking.edit_text("❌ Что-то пошло не так. Попробуй ещё раз.")
            await callback.message.answer("Что сделать с описанием?", reply_markup=baza_actions_keyboard())
            return
        await thinking.delete()
        for chunk in split_message(result):
            await callback.message.answer(chunk)
        await state.update_data(banner_prompts=banner_prompts)
        await state.set_state(OrderState.waiting_for_banner_pick)
        await callback.message.answer("Сгенерить баннер по одной из идей?", reply_markup=banner_pick_keyboard())
        return

    if action == "rename":
        thinking = await callback.message.answer("⏳ Подбираю варианты названия...")
        try:
            titles = await processor.analyzer.suggest_baza_titles(current_text)
        except Exception as e:
            logger.error("baza_rename_failed", error=str(e))
            await thinking.edit_text("❌ Что-то пошло не так. Попробуй ещё раз.")
            await callback.message.answer("Что сделать с описанием?", reply_markup=baza_actions_keyboard())
            return
        await thinking.delete()
        await state.update_data(baza_title_suggestions=titles)
        await state.set_state(OrderState.waiting_for_baza_rename)
        await callback.message.answer("Выбери вариант названия:", reply_markup=baza_title_keyboard(titles))
        return

    thinking = await callback.message.answer("⏳ Переделываю описание...")

    try:
        if action == "expand":
            result = await processor.analyzer.expand_baza(current_text)
        else:
            result = await processor.analyzer.shorten_baza(current_text)
    except Exception as e:
        logger.error("baza_action_failed", action=action, error=str(e))
        await thinking.edit_text("❌ Что-то пошло не так. Попробуй ещё раз.")
        await callback.message.answer("Что сделать с описанием?", reply_markup=baza_actions_keyboard())
        return

    await thinking.delete()
    await state.update_data(baza_result=result)

    data = await state.get_data()
    order_text: str = data.get("order_text", "")
    await HistoryService.save(callback.from_user.id, order_text, f"baza_{action}", result)

    for chunk in split_message(result):
        await callback.message.answer(chunk)

    await callback.message.answer("Что сделать с описанием?", reply_markup=baza_actions_keyboard())


@router.callback_query(F.data.startswith("baza_title:"), OrderState.waiting_for_baza_rename)
async def handle_baza_title_pick(callback: CallbackQuery, state: FSMContext) -> None:
    choice = callback.data.removeprefix("baza_title:")
    await callback.answer()

    if choice == "custom":
        await callback.message.answer("Введи своё название (первая строка заменится целиком):")
        await state.set_state(OrderState.waiting_for_baza_custom_title)
        return

    if choice == "back":
        await state.set_state(OrderState.waiting_for_baza_action)
        await callback.message.answer("Что сделать с описанием?", reply_markup=baza_actions_keyboard())
        return

    data = await state.get_data()
    titles: list[str] = data.get("baza_title_suggestions", [])
    current_text: str = data.get("baza_result", "")

    try:
        new_title = titles[int(choice)]
    except (IndexError, ValueError):
        await callback.message.answer("Что-то пошло не так. Попробуй снова.", reply_markup=baza_actions_keyboard())
        await state.set_state(OrderState.waiting_for_baza_action)
        return

    lines = current_text.split("\n", 1)
    updated_text = new_title + ("\n" + lines[1] if len(lines) > 1 else "")
    await state.update_data(baza_result=updated_text)

    order_text: str = data.get("order_text", "")
    await HistoryService.save(callback.from_user.id, order_text, "baza_rename", updated_text)

    for chunk in split_message(updated_text):
        await callback.message.answer(chunk)

    await state.set_state(OrderState.waiting_for_baza_action)
    await callback.message.answer("Что сделать с описанием?", reply_markup=baza_actions_keyboard())


@router.message(OrderState.waiting_for_baza_custom_title)
async def handle_baza_custom_title(message: Message, state: FSMContext) -> None:
    new_title = message.text.strip() if message.text else ""
    if not new_title:
        await message.answer("Название не может быть пустым. Попробуй снова:")
        return

    data = await state.get_data()
    current_text: str = data.get("baza_result", "")

    lines = current_text.split("\n", 1)
    updated_text = new_title + ("\n" + lines[1] if len(lines) > 1 else "")
    await state.update_data(baza_result=updated_text)

    order_text: str = data.get("order_text", "")
    await HistoryService.save(message.from_user.id, order_text, "baza_rename", updated_text)

    for chunk in split_message(updated_text):
        await message.answer(chunk)

    await state.set_state(OrderState.waiting_for_baza_action)
    await message.answer("Что сделать с описанием?", reply_markup=baza_actions_keyboard())


@router.callback_query(F.data.startswith("banner_gen:"), OrderState.waiting_for_banner_pick)
async def handle_banner_gen(callback: CallbackQuery, state: FSMContext, processor: OrderProcessor) -> None:
    choice = callback.data.removeprefix("banner_gen:")
    await callback.answer()

    if choice == "back":
        await state.set_state(OrderState.waiting_for_baza_action)
        await callback.message.answer("Что сделать с описанием?", reply_markup=baza_actions_keyboard())
        return

    data = await state.get_data()
    banner_prompts: list[str] = data.get("banner_prompts", [])

    try:
        idx = int(choice)
        prompt = banner_prompts[idx]
    except (ValueError, IndexError):
        await callback.message.answer("Не могу найти промпт. Попробуй снова.", reply_markup=banner_pick_keyboard())
        return

    thinking = await callback.message.answer(f"⏳ Генерирую баннер {idx + 1}...")
    logger.info("banner_gen_start", user_id=callback.from_user.id, idx=idx)

    try:
        image_bytes = await processor.analyzer.generate_banner_image(prompt)
    except Exception as e:
        logger.error("banner_gen_failed", idx=idx, error=str(e))
        await thinking.edit_text("❌ Не удалось сгенерировать баннер. Попробуй ещё раз.")
        await callback.message.answer("Попробуй другой вариант:", reply_markup=banner_pick_keyboard())
        return

    await thinking.delete()

    from aiogram.types import BufferedInputFile
    photo = BufferedInputFile(image_bytes, filename=f"banner_{idx + 1}.jpg")
    await callback.message.answer_photo(photo=photo, caption=f"🖼 Баннер {idx + 1}")
    await callback.message.answer("Сгенерить ещё один?", reply_markup=banner_pick_keyboard())


@router.callback_query(F.data.startswith("estimate_level:"), OrderState.waiting_for_estimate_level)
async def handle_estimate_level(callback: CallbackQuery, state: FSMContext, processor: OrderProcessor) -> None:
    level = callback.data.removeprefix("estimate_level:")
    await callback.answer()

    if level == "back":
        await state.set_state(OrderState.waiting_for_action)
        await callback.message.answer("Что ещё сделать?", reply_markup=actions_keyboard())
        return

    data = await state.get_data()
    order_text: str = data.get("order_text", "")

    cache_key = f"cache_estimate_{level}"
    if cached := data.get(cache_key):
        logger.info("estimate_cache_hit", level=level)
        for chunk in split_message(cached):
            await callback.message.answer(chunk)
        await state.set_state(OrderState.waiting_for_estimate_level)
        await callback.message.answer(
            "Оценить для другого уровня или вернуться в меню?",
            reply_markup=estimate_level_keyboard(),
        )
        return

    thinking = await callback.message.answer("⏳ Считаю стоимость и сроки...")
    logger.info("action_selected", user_id=callback.from_user.id, action=f"estimate_{level}")

    try:
        result = await processor.analyzer.estimate_cost(order_text, level)
    except Exception as e:
        logger.error("estimate_failed", level=level, error=str(e))
        await thinking.edit_text("❌ Что-то пошло не так. Попробуй ещё раз.")
        await state.set_state(OrderState.waiting_for_estimate_level)
        await callback.message.answer("Выбери уровень специалиста:", reply_markup=estimate_level_keyboard())
        return

    await thinking.delete()
    await HistoryService.save(callback.from_user.id, order_text, f"estimate_{level}", result)
    await state.update_data(**{cache_key: result})

    for chunk in split_message(result):
        await callback.message.answer(chunk)

    await state.set_state(OrderState.waiting_for_estimate_level)
    await callback.message.answer(
        "Оценить для другого уровня или вернуться в меню?",
        reply_markup=estimate_level_keyboard(),
    )


@router.callback_query(F.data.startswith("tg_bcat:"), OrderState.waiting_for_tg_birzha_category)
async def handle_tg_birzha_category(callback: CallbackQuery, state: FSMContext, processor: OrderProcessor) -> None:
    subtype = callback.data.removeprefix("tg_bcat:")
    await callback.answer()

    data = await state.get_data()
    order_text: str = data.get("order_text", "")

    thinking = await callback.message.answer("⏳ Оформляю заказ...")

    try:
        result = await processor.process(Action.TG, order_text)
    except Exception as e:
        logger.error("tg_format_failed", error=str(e))
        await thinking.edit_text("❌ Что-то пошло не так. Попробуй ещё раз.")
        await callback.message.answer("Что ещё сделать?", reply_markup=actions_keyboard())
        return

    await thinking.delete()
    await HistoryService.save(callback.from_user.id, order_text, "tg", result)

    banner_path = get_random_banner("zakazyi", "birzha", subtype)
    if banner_path:
        photo = FSInputFile(str(banner_path))
        caption = result if len(result) <= 1024 else None
        await callback.message.answer_photo(photo=photo, caption=caption)
        if caption is None:
            for chunk in split_message(result):
                await callback.message.answer(chunk)
    else:
        for chunk in split_message(result):
            await callback.message.answer(chunk)

    await state.update_data(tg_result=result, tg_format_type="order")
    await state.set_state(OrderState.waiting_for_tg_edit)
    await callback.message.answer("Изменить описание?", reply_markup=tg_edit_keyboard())


@router.callback_query(F.data.startswith("tg_edit:"), OrderState.waiting_for_tg_edit)
async def handle_tg_edit(callback: CallbackQuery, state: FSMContext, processor: OrderProcessor) -> None:
    action = callback.data.removeprefix("tg_edit:")
    await callback.answer()

    if action == "done":
        await state.set_state(OrderState.waiting_for_action)
        await callback.message.answer("Что ещё сделать?", reply_markup=actions_keyboard())
        return

    data = await state.get_data()
    current_text: str = data.get("tg_result", "")
    is_vacancy = data.get("tg_format_type") == "vacancy"

    thinking = await callback.message.answer(
        "⏳ Сокращаю..." if action == "shorten" else "⏳ Расширяю..."
    )

    try:
        if action == "shorten":
            result = await (
                processor.analyzer.shorten_vacancy_tg(current_text)
                if is_vacancy
                else processor.analyzer.shorten_tg(current_text)
            )
        else:
            result = await (
                processor.analyzer.expand_vacancy_tg(current_text)
                if is_vacancy
                else processor.analyzer.expand_tg(current_text)
            )
    except Exception as e:
        logger.error("tg_edit_failed", action=action, error=str(e))
        await thinking.edit_text("❌ Что-то пошло не так. Попробуй ещё раз.")
        await callback.message.answer("Изменить описание?", reply_markup=tg_edit_keyboard())
        return

    await thinking.delete()
    await state.update_data(tg_result=result)

    order_text: str = data.get("order_text", "")
    await HistoryService.save(callback.from_user.id, order_text, f"tg_{action}", result)

    for chunk in split_message(result):
        await callback.message.answer(chunk)

    await callback.message.answer("Изменить описание?", reply_markup=tg_edit_keyboard())


@router.callback_query(F.data.startswith("tg_channel:"), OrderState.waiting_for_tg_channel)
async def handle_tg_channel(callback: CallbackQuery, state: FSMContext) -> None:
    channel = callback.data.removeprefix("tg_channel:")
    await callback.answer()

    if channel == "pesochnica":
        await state.set_state(OrderState.waiting_for_tg_pesochnica_type)
        await callback.message.answer("Тип публикации:", reply_markup=tg_pesochnica_type_keyboard())
    else:
        await state.update_data(banner_category="frilans")
        await state.set_state(OrderState.waiting_for_tg_subchannel)
        await callback.message.answer("Направление:", reply_markup=tg_frilans_keyboard())


@router.callback_query(F.data.startswith("tg_ptype:"), OrderState.waiting_for_tg_pesochnica_type)
async def handle_tg_pesochnica_type(callback: CallbackQuery, state: FSMContext) -> None:
    ptype = callback.data.removeprefix("tg_ptype:")
    await callback.answer()
    await state.update_data(banner_category=ptype)
    await state.set_state(OrderState.waiting_for_tg_subchannel)
    await callback.message.answer("Площадка:", reply_markup=tg_pesochnica_keyboard())


@router.callback_query(F.data.startswith("tg_sub:"), OrderState.waiting_for_tg_subchannel)
async def handle_tg_subchannel(callback: CallbackQuery, state: FSMContext, processor: OrderProcessor) -> None:
    subchannel = callback.data.removeprefix("tg_sub:")
    await callback.answer()

    data = await state.get_data()
    banner_category: str = data.get("banner_category", "")
    order_text: str = data.get("order_text", "")

    if banner_category == "zakazyi" and subchannel == "birzha":
        await state.set_state(OrderState.waiting_for_tg_birzha_category)
        await callback.message.answer("Категория заказа:", reply_markup=tg_birzha_category_keyboard())
        return

    thinking = await callback.message.answer("⏳ Оформляю заказ...")

    try:
        if banner_category == "pesochnica":
            result = await processor.analyzer.format_vacancy_for_tg(order_text)
        elif banner_category == "frilans":
            result = await processor.analyzer.format_for_tg(order_text)
            result = _strip_hashtag_lines(result)
            result += "\n\n#Python" if subchannel == "python" else "\n\n#prompt"
        else:
            result = await processor.analyzer.format_for_tg(order_text)
    except Exception as e:
        logger.error("tg_format_failed", error=str(e))
        await thinking.edit_text("❌ Что-то пошло не так. Попробуй ещё раз.")
        await callback.message.answer("Что ещё сделать?", reply_markup=actions_keyboard())
        return

    await thinking.delete()
    await HistoryService.save(callback.from_user.id, order_text, f"tg_{banner_category}_{subchannel}", result)

    banner_path = get_random_banner(banner_category, subchannel)
    if banner_path:
        photo = FSInputFile(str(banner_path))
        caption = result if len(result) <= 1024 else None
        await callback.message.answer_photo(photo=photo, caption=caption)
        if caption is None:
            for chunk in split_message(result):
                await callback.message.answer(chunk)
    else:
        for chunk in split_message(result):
            await callback.message.answer(chunk)

    fmt_type = "vacancy" if banner_category == "pesochnica" else "order"
    await state.update_data(tg_result=result, tg_format_type=fmt_type)
    await state.set_state(OrderState.waiting_for_tg_edit)
    await callback.message.answer("Изменить описание?", reply_markup=tg_edit_keyboard())
