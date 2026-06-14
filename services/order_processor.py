from __future__ import annotations

import time

import structlog

from ai.analyzer import Analyzer
from bot.keyboards.actions import Action

logger = structlog.get_logger()


class OrderProcessor:
    def __init__(self) -> None:
        self.analyzer = Analyzer()

    async def process(self, action: Action, order_text: str) -> str:
        start = time.monotonic()
        logger.info("ai_call_start", action=action.value)

        match action:
            case Action.STEK:
                result = await self.analyzer.detect_stack(order_text)
            case Action.SOOTVETSTVIE:
                result = await self.analyzer.match_skillset(order_text)
            case Action.BAZA:
                result = await self.analyzer.format_for_base(order_text)
            case Action.TG:
                result = await self.analyzer.format_for_tg(order_text)
            case _:
                result = "Неизвестное действие."

        elapsed = int((time.monotonic() - start) * 1000)
        logger.info("ai_call_done", action=action.value, duration_ms=elapsed)

        return result
