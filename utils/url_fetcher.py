from __future__ import annotations

from html.parser import HTMLParser

import httpx

_SKIP_TAGS = {"script", "style", "head", "nav", "footer", "header", "noscript", "meta", "link"}
_MIN_CHARS = 200


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip: int = 0

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag.lower() in _SKIP_TAGS:
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in _SKIP_TAGS:
            self._skip = max(0, self._skip - 1)

    def handle_data(self, data: str) -> None:
        if not self._skip:
            stripped = data.strip()
            if stripped:
                self._parts.append(stripped)

    def get_text(self) -> str:
        return "\n".join(self._parts)


async def fetch_order_text(url: str, max_chars: int = 12000) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()

    content_type = response.headers.get("content-type", "")
    if "text/html" not in content_type:
        raise ValueError(f"Страница не HTML: {content_type}")

    parser = _TextExtractor()
    parser.feed(response.text)
    text = parser.get_text()

    if len(text) < _MIN_CHARS:
        raise ValueError(
            "Не удалось извлечь текст со страницы — "
            "возможно, сайт требует авторизации или использует динамическую загрузку."
        )

    if len(text) > max_chars:
        text = text[:max_chars] + "\n...[текст обрезан]"

    return text
