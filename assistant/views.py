import json
import logging
import re
import uuid

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from core.ratelimit import is_rate_limited
from support.models import SupportTicket

from . import mongo
from .llm import AIUnavailable, generate_answer
from .retrieval import retrieve

logger = logging.getLogger("gather.assistant")

MAX_BODY_BYTES = 4096
PAGE_CONTEXTS = {
    "error_404": "The visitor reached a missing page (HTTP 404 Not Found)",
    "error_500": "The visitor saw a server error page (HTTP 500 Internal Server Error)",
}
UUID_RE = re.compile(r"^[0-9a-f]{32}$")
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[A-Za-z]{2,24}$")


def error(message, status, code=None):
    payload = {"ok": False, "error": message}
    if code:
        payload["code"] = code
    return JsonResponse(payload, status=status)


def read_json(request):
    if len(request.body) > MAX_BODY_BYTES:
        return None, error("Your message is too large.", 413)
    try:
        data = json.loads(request.body or b"{}")
    except (ValueError, UnicodeDecodeError):
        return None, error("The request could not be read (400 Bad Request).", 400)
    if not isinstance(data, dict):
        return None, error("The request could not be read (400 Bad Request).", 400)
    return data, None


def conversation_id(request):
    """A random pseudonymous ID kept in the visitor's session – no account needed."""
    cid = request.session.get("conversation_id")
    if not cid:
        cid = uuid.uuid4().hex
        request.session["conversation_id"] = cid
    return cid


def remember_message(request, message_id, question):
    recent = request.session.get("recent_messages", [])
    recent.append({"id": message_id, "q": question[:300]})
    request.session["recent_messages"] = recent[-30:]


def find_recent_message(request, message_id):
    for item in request.session.get("recent_messages", []):
        if item["id"] == message_id:
            return item
    return None


def fallback_answer(retrieval):
    lines = []
    for code in retrieval.error_codes:
        lines.append(f"**{code.code} {code.name}** – {code.meaning}")
        lines.append("Common causes: " + "; ".join(code.causes_list) + ".")
        lines.append("Try: " + "; ".join(code.steps_list) + ".")
        lines.append("Next step: " + code.next_action)
    for faq, _ in retrieval.faqs:
        lines.append(f"**{faq.question}** {faq.answer}")
    for product, _ in retrieval.products:
        lines.append(f"**{product.name}** – ${product.daily_rate}/day, {product.quantity_total} in stock. "
                     f"See {product.get_absolute_url()}")
    return "\n\n".join(lines)


@require_POST
def chat(request):
    if is_rate_limited(request, "chat", settings.CHAT_RATE_LIMIT, window=60):
        return error("You're sending messages too quickly (429 Too Many Requests). Please wait a minute.", 429)
    data, problem = read_json(request)
    if problem:
        return problem
    question = str(data.get("message", "")).strip()
    if not question:
        return error("Please type a question first.", 400)
    if len(question) > settings.ASSISTANT_MAX_QUESTION_LENGTH:
        return error(f"Please keep questions under {settings.ASSISTANT_MAX_QUESTION_LENGTH} characters.", 400)
    page_context = PAGE_CONTEXTS.get(str(data.get("context", "")), "")
    page_path = str(data.get("path", ""))[:200] if page_context else ""

    search_text = question
    if data.get("context") == "error_404":
        search_text += " 404 not found"
    elif data.get("context") == "error_500":
        search_text += " 500 internal server error"
    retrieval = retrieve(search_text)

    cid = conversation_id(request)
    message_id = uuid.uuid4().hex
    remember_message(request, message_id, question)

    if retrieval.unknown_codes and not retrieval.error_codes:
        codes = ", ".join(str(c) for c in retrieval.unknown_codes)
        answer = (f"I don't have a verified explanation for code {codes}, so I won't guess. "
                  "Our Error Code Reference covers 400, 401, 403, 404, 429, 500, 503 and 4600. "
                  "Would you like me to create a support ticket?")
        source = "no_answer"
    elif not retrieval.is_confident:
        answer = ("I'm not sure about that – I couldn't find it in our FAQs, inventory or error-code reference, "
                  "and I don't want to give you incorrect information. Would you like me to create a support "
                  "ticket so a person can help?")
        source = "no_answer"
    else:
        context_note = f"{page_context} at path {page_path}" if page_context else ""
        try:
            answer = generate_answer(question, retrieval, context_note)
            source = "ai"
        except AIUnavailable:
            answer = fallback_answer(retrieval)
            source = "fallback"

    mongo.log_chat(
        conversation_id=cid, message_id=message_id, question=question, answer=answer,
        faq_ids=retrieval.faq_ids, error_codes=[c.code for c in retrieval.error_codes],
        ticket_created=False, source=source,
    )
    payload = {
        "ok": True,
        "message_id": message_id,
        "answer": answer,
        "source": source,
        "offer_ticket": source == "no_answer",
        "faqs": [{"id": f.id, "question": f.question} for f, _ in retrieval.faqs],
        "error_codes": [c.code for c in retrieval.error_codes],
    }
    if source == "fallback":
        payload["code"] = 4600
        payload["notice"] = ("AI_ASSISTANT_UNAVAILABLE (4600): the AI service isn't available right now, "
                             "so this is the matching text from our FAQ and error-code database, not an AI answer.")
    return JsonResponse(payload)


@require_POST
def create_ticket(request):
    if is_rate_limited(request, "ticket", settings.TICKET_RATE_LIMIT, window=600):
        return error("Too many tickets were created from your connection (429). Please wait a few minutes.", 429)
    data, problem = read_json(request)
    if problem:
        return problem
    message_id = str(data.get("message_id", ""))
    item = find_recent_message(request, message_id) if UUID_RE.match(message_id) else None
    if item is None:
        return error("That conversation message could not be found. Please ask your question again.", 400)
    email = str(data.get("email", "")).strip()[:254]
    if email and not EMAIL_RE.match(email):
        return error("Please enter a valid email address, or leave it empty.", 400)

    cid = conversation_id(request)
    ticket = SupportTicket.objects.create(
        subject=("Assistant question: " + item["q"])[:150],
        description=f"The assistant could not answer this question:\n\n{item['q']}",
        category=SupportTicket.Category.ASSISTANT,
        email=email,
        conversation_id=cid,
    )
    mongo.log_chat(
        conversation_id=cid, message_id=uuid.uuid4().hex, question=item["q"],
        answer=f"Support ticket {ticket.reference} created.", faq_ids=[], error_codes=[],
        ticket_created=True, source="ticket",
    )
    return JsonResponse({"ok": True, "reference": ticket.reference})


@require_POST
def feedback(request):
    if is_rate_limited(request, "feedback", settings.CHAT_RATE_LIMIT, window=60):
        return error("Too many feedback submissions. Please wait a minute.", 429)
    data, problem = read_json(request)
    if problem:
        return problem
    message_id = str(data.get("message_id", ""))
    if not UUID_RE.match(message_id) or find_recent_message(request, message_id) is None:
        return error("Unknown message.", 400)
    rating = data.get("rating")
    if not isinstance(rating, int) or isinstance(rating, bool) or not 1 <= rating <= 5:
        return error("Rating must be a whole number from 1 to 5.", 400)
    comment = str(data.get("comment", "")).strip()
    if len(comment) > 500:
        return error("Feedback must be 500 characters or fewer.", 400)
    stored = mongo.save_feedback(conversation_id(request), message_id, rating, comment)
    if not stored:
        return JsonResponse({"ok": True, "stored": False,
                             "notice": "Thanks! (Feedback storage is temporarily unavailable, so it wasn't saved.)"})
    return JsonResponse({"ok": True, "stored": True})
