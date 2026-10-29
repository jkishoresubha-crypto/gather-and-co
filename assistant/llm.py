"""Server-side call to the AI provider (OpenAI Chat Completions API).

The API key never leaves the server. Any failure raises AIUnavailable so the
caller can fall back to the retrieved FAQ text (error code 4600).
"""
import logging

import requests
from django.conf import settings

logger = logging.getLogger("gather.assistant")

SYSTEM_PROMPT = (
    "You are the customer assistant for Gather & Co., an event-rental inventory website where customers "
    "reserve items through bookings and the owner confirms them. Answer ONLY using the facts in the "
    "CONTEXT section. Do not invent policies, prices, stock levels, booking records, error explanations or "
    "any other facts that are not in the context. If the context does not answer the question, say clearly "
    "that you are not sure and suggest creating a support ticket. When explaining an error code, cover: what "
    "it means, common causes, how to troubleshoot, and when to contact support. Note that 4600 is a Gather & Co. "
    "application code, not an HTTP status. Keep answers short (under 150 words), friendly and in plain language."
)


class AIUnavailable(Exception):
    pass


def build_context(retrieval):
    parts = []
    for faq, _ in retrieval.faqs:
        parts.append(f"FAQ #{faq.id}: Q: {faq.question}\nA: {faq.answer}")
    for code in retrieval.error_codes:
        parts.append(
            f"ERROR CODE {code.code} {code.name} ({code.get_kind_display()}):\nMeaning: {code.meaning}\n"
            f"Common causes: {'; '.join(code.causes_list)}\nTroubleshooting: {'; '.join(code.steps_list)}\n"
            f"Next action: {code.next_action}"
        )
    for product, _ in retrieval.products:
        parts.append(
            f"PRODUCT: {product.name} (category {product.category.name}), ${product.daily_rate} per day, "
            f"{product.quantity_total} units in total stock. {product.description} Page: {product.get_absolute_url()}"
        )
    return "\n\n".join(parts) or "(no relevant information found)"


def generate_answer(question, retrieval, page_context=""):
    if not settings.OPENAI_API_KEY:
        raise AIUnavailable("not configured")
    user_message = f"CONTEXT:\n{build_context(retrieval)}\n\n"
    if page_context:
        user_message += f"PAGE CONTEXT: {page_context}\n\n"
    user_message += f"QUESTION: {question}"
    try:
        response = requests.post(
            settings.OPENAI_API_URL,
            headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": settings.OPENAI_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                "temperature": 0.2,
                "max_tokens": 350,
            },
            timeout=(5, settings.AI_TIMEOUT_SECONDS),
        )
    except requests.RequestException as exc:
        logger.warning("AI provider request failed error=%s", type(exc).__name__)
        raise AIUnavailable("request failed") from exc
    if response.status_code != 200:
        logger.warning("AI provider returned status=%s", response.status_code)
        raise AIUnavailable(f"status {response.status_code}")
    try:
        text = response.json()["choices"][0]["message"]["content"].strip()
    except (ValueError, KeyError, IndexError, TypeError, AttributeError) as exc:
        logger.warning("AI provider returned a malformed response")
        raise AIUnavailable("malformed response") from exc
    if not text:
        raise AIUnavailable("empty response")
    return text
