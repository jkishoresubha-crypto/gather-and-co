"""Retrieval-first knowledge lookup for the assistant.

1. Detect error codes mentioned in the question (e.g. "404", "4600").
2. Pre-filter active FAQs and products in the database with ORM `icontains`
   queries on the question's keywords.
3. Score each candidate by keyword overlap and keep those above the
   relevance threshold (settings.ASSISTANT_RELEVANCE_THRESHOLD).
"""
import re
from dataclasses import dataclass, field

from django.conf import settings
from django.db.models import Q

from faqs.models import FAQ, ErrorCode
from inventory.models import Product

STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "to", "of", "and", "or", "in", "on", "at", "for",
    "with", "my", "me", "i", "you", "your", "it", "this", "that", "do", "does", "did", "can", "could",
    "how", "what", "why", "when", "where", "which", "who", "please", "hi", "hello", "hey", "there", "about",
    "get", "got", "have", "has", "will", "would", "should", "if", "so", "any", "some", "we", "our", "us",
    "tell", "explain", "mean", "means", "meaning", "know", "want", "need", "help", "thanks", "thank",
}
NAME_TO_CODE = {
    "bad request": 400, "unauthorized": 401, "forbidden": 403, "not found": 404,
    "too many requests": 429, "rate limit": 429, "internal server error": 500,
    "service unavailable": 503, "ai_assistant_unavailable": 4600, "assistant unavailable": 4600,
}
CODE_PATTERN = re.compile(r"\b(\d{3,4})\b")


@dataclass
class RetrievalResult:
    faqs: list = field(default_factory=list)          # list of (FAQ, score)
    products: list = field(default_factory=list)      # list of (Product, score)
    error_codes: list = field(default_factory=list)   # list of ErrorCode
    unknown_codes: list = field(default_factory=list)  # numbers that look like codes but are not documented
    top_score: float = 0.0

    @property
    def is_confident(self):
        return bool(self.error_codes) or self.top_score >= settings.ASSISTANT_RELEVANCE_THRESHOLD

    @property
    def faq_ids(self):
        return [faq.id for faq, _ in self.faqs]


def tokenize(text):
    words = re.findall(r"[a-z0-9]+", text.lower())
    terms = []
    for word in words:
        # Skip filler words and short tokens; small numbers ("50 guests") carry no topic.
        if word in STOPWORDS or len(word) < 3:
            continue
        # very light stemming so "bookings" matches "booking"
        if len(word) > 4 and word.endswith("s"):
            word = word[:-1]
        if word not in terms:
            terms.append(word)
    return terms[:12]


def detect_error_codes(text):
    lowered = text.lower()
    numbers = {int(n) for n in CODE_PATTERN.findall(text)}
    numbers |= {code for name, code in NAME_TO_CODE.items() if name in lowered}
    known = {ec.code: ec for ec in ErrorCode.objects.filter(code__in=numbers)}
    unknown = sorted(n for n in numbers if n not in known and (400 <= n <= 599 or 4000 <= n <= 4999))
    return [known[c] for c in sorted(known)], unknown


def phrases(text):
    """Two-word phrases from the raw question, e.g. "my bookings", "log in"."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {f"{a} {b}" for a, b in zip(words, words[1:]) if not (a in STOPWORDS and b in STOPWORDS)}


def score(terms, primary, secondary, question_phrases=()):
    if not terms:
        return 0.0
    primary, secondary = primary.lower(), secondary.lower()
    total = 0.0
    for term in terms:
        if term in primary:
            total += 1.0
        elif term in secondary:
            total += 0.25
    # Small bonus when an exact phrase from the question appears in the FAQ title/keywords.
    bonus = min(0.3 * sum(1 for p in question_phrases if p in primary), 0.6)
    return round(total / len(terms) + bonus, 3)


def best(scored, threshold):
    """Keep matches above the threshold that are also close to the best match,
    so one strong hit is not diluted by several weak ones."""
    top = max((s for _, s in scored), default=0.0)
    cutoff = max(threshold, top * 0.6)
    return sorted([item for item in scored if item[1] >= cutoff], key=lambda item: -item[1])


def retrieve(question, max_faqs=3, max_products=3):
    result = RetrievalResult()
    result.error_codes, result.unknown_codes = detect_error_codes(question)
    terms = tokenize(question)
    if not terms:
        return result

    term_filter = Q()
    for term in terms:
        term_filter |= Q(question__icontains=term) | Q(keywords__icontains=term) | Q(answer__icontains=term)
    faq_candidates = FAQ.objects.filter(is_active=True).filter(term_filter)[:50]
    question_phrases = phrases(question)
    scored = [(faq, score(terms, f"{faq.question} {faq.keywords}", faq.answer, question_phrases))
              for faq in faq_candidates]
    threshold = settings.ASSISTANT_RELEVANCE_THRESHOLD
    if result.error_codes:
        # The question is about specific codes: drop FAQs that describe *other* codes.
        wanted = {str(c.code) for c in result.error_codes}
        scored = [(f, s) for f, s in scored
                  if wanted & set(CODE_PATTERN.findall(f.question)) or not CODE_PATTERN.findall(f.question)]
    result.faqs = best(scored, threshold)[:max_faqs]

    product_filter = Q()
    for term in terms:
        product_filter |= Q(name__icontains=term) | Q(category__name__icontains=term) | Q(description__icontains=term)
    product_candidates = Product.objects.filter(is_active=True).filter(product_filter).select_related("category")[:30]
    scored_products = [
        (p, score(terms, f"{p.name} {p.category.name}", p.description)) for p in product_candidates
    ]
    result.products = best(scored_products, threshold)[:max_products]

    scores = [s for _, s in result.faqs] + [s for _, s in result.products]
    result.top_score = max(scores, default=0.0)
    return result
