from __future__ import annotations

import json
import re
import asyncio

import httpx
import requests
from anthropic import APIConnectionError, APIStatusError, APITimeoutError, AsyncAnthropic
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from ai import prompts
from ai.client import get_client
from bot.config import settings
from utils.skillset_loader import load_skillset

_RETRY = dict(
    retry=retry_if_exception_type((APIStatusError, APITimeoutError, APIConnectionError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=1, max=8),
    reraise=True,
)


class Analyzer:
    def __init__(self) -> None:
        self.client: AsyncAnthropic = get_client()
        self.model: str = settings.anthropic_model
        self.skillset: str = load_skillset()

    async def _call(self, system: str, user: str, temperature: float) -> str:
        async for attempt in AsyncRetrying(**_RETRY):
            with attempt:
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=2048,
                    temperature=temperature,
                    system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
                    messages=[{"role": "user", "content": user}],
                )
        return response.content[0].text

    async def detect_stack(self, order_text: str) -> str:
        return await self._call(
            system=prompts.stack_detect.system(self.skillset),
            user=prompts.stack_detect.user(order_text),
            temperature=0.3,
        )

    async def match_skillset(self, order_text: str) -> str:
        return await self._call(
            system=prompts.skillset_match.system(self.skillset),
            user=prompts.skillset_match.user(order_text),
            temperature=0.3,
        )

    async def generate_response_developer(self, order_text: str) -> str:
        return await self._call(
            system=prompts.response_gen.system_developer(self.skillset),
            user=prompts.response_gen.user(order_text),
            temperature=0.7,
        )

    async def generate_response_team(self, order_text: str) -> str:
        return await self._call(
            system=prompts.response_gen.system_team(self.skillset),
            user=prompts.response_gen.user(order_text),
            temperature=0.7,
        )

    async def format_for_base(self, order_text: str) -> str:
        return await self._call(
            system=prompts.order_format_base.system(self.skillset),
            user=prompts.order_format_base.user(order_text),
            temperature=0.7,
        )

    async def expand_baza(self, current_text: str) -> str:
        return await self._call(
            system=prompts.order_format_base.system(self.skillset),
            user=prompts.order_format_base.expand_user(current_text),
            temperature=0.7,
        )

    async def shorten_baza(self, current_text: str) -> str:
        return await self._call(
            system=prompts.order_format_base.system(self.skillset),
            user=prompts.order_format_base.shorten_user(current_text),
            temperature=0.7,
        )

    async def suggest_baza_titles(self, current_text: str) -> list[str]:
        raw = await self._call(
            system=prompts.order_format_base.system(self.skillset),
            user=prompts.order_format_base.suggest_titles_user(current_text),
            temperature=0.7,
        )
        raw = raw.strip()
        start = raw.find("[")
        end = raw.rfind("]")
        if start != -1 and end != -1:
            titles = json.loads(raw[start : end + 1])
            return [str(t) for t in titles[:3]]
        return [line.strip() for line in raw.splitlines() if line.strip()][:3]

    async def format_for_tg(self, order_text: str) -> str:
        return await self._call(
            system=prompts.order_format_tg.system(self.skillset),
            user=prompts.order_format_tg.user(order_text),
            temperature=0.7,
        )

    async def expand_tg(self, current_text: str) -> str:
        return await self._call(
            system=prompts.order_format_tg.system(self.skillset),
            user=prompts.order_format_tg.expand_user(current_text),
            temperature=0.7,
        )

    async def shorten_tg(self, current_text: str) -> str:
        return await self._call(
            system=prompts.order_format_tg.system(self.skillset),
            user=prompts.order_format_tg.shorten_user(current_text),
            temperature=0.7,
        )

    async def expand_vacancy_tg(self, current_text: str) -> str:
        return await self._call(
            system=prompts.vacancy_format_tg.system(self.skillset),
            user=prompts.vacancy_format_tg.expand_user(current_text),
            temperature=0.7,
        )

    async def shorten_vacancy_tg(self, current_text: str) -> str:
        return await self._call(
            system=prompts.vacancy_format_tg.system(self.skillset),
            user=prompts.vacancy_format_tg.shorten_user(current_text),
            temperature=0.7,
        )

    async def suggest_banners(self, order_text: str) -> tuple[str, list[str]]:
        raw = await self._call(
            system=prompts.banner_ideas.system(),
            user=prompts.banner_ideas.user(order_text),
            temperature=0.8,
        )
        prompts_list = re.findall(r"Промпт:\s*(.+?)(?=\n🎨|\Z)", raw, re.DOTALL)
        prompts_list = [p.strip() for p in prompts_list]
        return raw, prompts_list

    async def generate_banner_image(self, prompt: str) -> bytes:
        def _fetch() -> bytes:
            url = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"
            headers = {"Authorization": f"Bearer {settings.hf_token}"}
            response = requests.post(url, headers=headers, json={"inputs": prompt}, timeout=120)
            response.raise_for_status()
            return response.content
        return await asyncio.to_thread(_fetch)

    async def format_vacancy_for_tg(self, order_text: str) -> str:
        return await self._call(
            system=prompts.vacancy_format_tg.system(self.skillset),
            user=prompts.vacancy_format_tg.user(order_text),
            temperature=0.7,
        )

    async def estimate_cost(self, order_text: str, level: str) -> str:
        return await self._call(
            system=prompts.estimate.system(level),
            user=prompts.estimate.user(order_text),
            temperature=0.3,
        )
