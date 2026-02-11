"""Async OpenAI-compatible client for llama.cpp server."""

from openai import AsyncOpenAI
import config


_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            base_url=config.LLM_BASE_URL,
            api_key=config.LLM_API_KEY,
        )
    return _client


async def chat(messages: list[dict], temperature: float | None = None) -> str:
    """Send a chat completion request and return the response text."""
    client = get_client()
    response = await client.chat.completions.create(
        model=config.LLM_MODEL,
        messages=messages,
        temperature=temperature or config.LLM_TEMPERATURE,
        max_tokens=config.LLM_MAX_TOKENS,
    )
    return response.choices[0].message.content or ""
