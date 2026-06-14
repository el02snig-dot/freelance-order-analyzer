from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from ddgs import DDGS

from ai.client import get_client
from bot.config import settings

_RESULTS_DIR = Path(__file__).parent.parent.parent / "research_results"

# --------------------------------------------------------------------------- #
# Result dataclass
# --------------------------------------------------------------------------- #

@dataclass
class ResearchResult:
    topic: str
    summary: str
    key_points: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)

    def to_text(self) -> str:
        lines = [f"**Тема:** {self.topic}", "", f"**Резюме:** {self.summary}"]
        if self.key_points:
            lines += ["", "**Ключевые факты:**"]
            lines += [f"• {p}" for p in self.key_points]
        if self.sources:
            lines += ["", "**Источники:**"]
            lines += [f"— {s}" for s in self.sources]
        return "\n".join(lines)

    def save(self) -> Path:
        _RESULTS_DIR.mkdir(exist_ok=True)
        slug = re.sub(r"[^\w\-]", "_", self.topic[:50]).strip("_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = _RESULTS_DIR / f"{timestamp}_{slug}.json"
        path.write_text(
            json.dumps(
                {
                    "topic": self.topic,
                    "summary": self.summary,
                    "key_points": self.key_points,
                    "sources": self.sources,
                    "saved_at": datetime.now().isoformat(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return path


# --------------------------------------------------------------------------- #
# Tool implementations
# --------------------------------------------------------------------------- #

async def _web_search(query: str, max_results: int = 5) -> str:
    """Run DDG search in a thread so it doesn't block the event loop."""
    def _sync() -> list[dict]:
        return list(DDGS().text(query, max_results=max_results))

    try:
        results = await asyncio.to_thread(_sync)
    except Exception as e:
        return f"Ошибка поиска: {e}"

    if not results:
        return "Поиск не вернул результатов."

    lines: list[str] = []
    for i, r in enumerate(results, 1):
        lines.append(
            f"{i}. {r.get('title', '').strip()}\n"
            f"   {r.get('href', '')}\n"
            f"   {r.get('body', '')[:200].strip()}"
        )
    return "\n\n".join(lines)


async def _fetch_page(url: str) -> str:
    from utils.url_fetcher import fetch_order_text
    try:
        return await fetch_order_text(url, max_chars=6000)
    except Exception as e:
        return f"Не удалось загрузить страницу: {e}"


# --------------------------------------------------------------------------- #
# Tool schemas
# --------------------------------------------------------------------------- #

_TOOLS: list[dict[str, Any]] = [
    {
        "name": "web_search",
        "description": (
            "Выполняет поиск в интернете по запросу. "
            "Возвращает список результатов: заголовок, URL, сниппет."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Поисковый запрос"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "fetch_page",
        "description": "Загружает полный текст веб-страницы по URL для детального изучения.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL страницы"},
            },
            "required": ["url"],
        },
    },
]

_SYSTEM = """\
Ты — агент-исследователь. Получив тему, собери актуальную информацию с помощью инструментов.

Алгоритм:
1. Сделай 1–3 поисковых запроса по теме (пробуй разные формулировки, в т.ч. на русском и английском)
2. При необходимости открой 1–2 наиболее релевантных страницы
3. Синтезируй найденное в структурированный ответ

Когда соберёшь достаточно данных, верни ТОЛЬКО валидный JSON без markdown-блоков:
{
  "summary": "краткое резюме в 2–4 предложениях",
  "key_points": ["ключевой факт 1", "ключевой факт 2", "ключевой факт 3"],
  "sources": ["https://url1", "https://url2"]
}

Если информацию найти не удалось — всё равно верни JSON с объяснением в summary.\
"""


# --------------------------------------------------------------------------- #
# Agent
# --------------------------------------------------------------------------- #

class ResearcherAgent:
    """
    Sub-agent: researches a topic via web search and returns a structured result.

    Usage:
        agent = ResearcherAgent()
        result = await agent.research("Средние ставки Python-разработчиков 2024")
        print(result.to_text())
    """

    def __init__(self) -> None:
        self.client = get_client()
        self.model = settings.anthropic_model

    async def research(self, topic: str, max_steps: int = 8) -> ResearchResult:
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": f"Исследуй тему: {topic}"},
        ]

        for _ in range(max_steps):
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=_SYSTEM,
                tools=_TOOLS,
                messages=messages,
            )

            if response.stop_reason == "end_turn":
                text = "".join(
                    b.text for b in response.content if hasattr(b, "text")
                )
                result = self._parse(topic, text)
                result.save()
                return result

            if response.stop_reason == "tool_use":
                tool_results: list[dict[str, Any]] = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue
                    if block.name == "web_search":
                        output = await _web_search(block.input["query"])
                    elif block.name == "fetch_page":
                        output = await _fetch_page(block.input["url"])
                    else:
                        output = f"Инструмент '{block.name}' не найден."

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": output,
                    })

                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})

        return ResearchResult(
            topic=topic,
            summary="Агент превысил лимит шагов. Попробуй сузить тему запроса.",
        )

    @staticmethod
    def _parse(topic: str, text: str) -> ResearchResult:
        text = text.strip()
        start, end = text.find("{"), text.rfind("}") + 1
        if start != -1 and end > start:
            try:
                data = json.loads(text[start:end])
                return ResearchResult(
                    topic=topic,
                    summary=str(data.get("summary", "")),
                    key_points=[str(p) for p in data.get("key_points", [])],
                    sources=[str(s) for s in data.get("sources", [])],
                )
            except json.JSONDecodeError:
                pass
        return ResearchResult(topic=topic, summary=text)
