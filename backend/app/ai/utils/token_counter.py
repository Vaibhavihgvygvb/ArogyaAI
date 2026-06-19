import math


def estimate_tokens(text: str) -> int:
    return max(1, math.ceil(len(text) / 4))


def estimate_messages_tokens(messages: list[dict]) -> int:
    total = 0
    for msg in messages:
        total += estimate_tokens(msg.get("content", ""))
        total += 4
    return total


def truncate_to_token_limit(text: str, max_tokens: int) -> str:
    if estimate_tokens(text) <= max_tokens:
        return text
    chars_per_token = 4
    max_chars = max_tokens * chars_per_token
    return text[:max_chars]


def truncate_messages(messages: list[dict], max_tokens: int) -> list[dict]:
    result = list(messages)
    while result and estimate_messages_tokens(result) > max_tokens:
        removed = result.pop(0)
        if removed.get("role") == "system" and result:
            result.pop(0)
    return result
