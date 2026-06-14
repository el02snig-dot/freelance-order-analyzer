from __future__ import annotations

import asyncio

import structlog
from aiogram import Bot, Dispatcher

from bot.config import settings
from bot.handlers import actions, common, order
from bot.middlewares.access import AccessMiddleware
from bot.storage import SqliteStorage
from services.history_service import HistoryService
from services.order_processor import OrderProcessor

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ]
)

logger = structlog.get_logger()


async def main() -> None:
    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher(storage=SqliteStorage("fsm.db"))

    dp.message.middleware(AccessMiddleware(settings.allowed_user_ids))
    dp.callback_query.middleware(AccessMiddleware(settings.allowed_user_ids))

    dp.include_router(common.router)
    dp.include_router(order.router)
    dp.include_router(actions.router)

    await HistoryService.init_db()

    processor = OrderProcessor()
    logger.info("bot_starting", model=settings.anthropic_model)
    await dp.start_polling(bot, processor=processor)


if __name__ == "__main__":
    asyncio.run(main())
