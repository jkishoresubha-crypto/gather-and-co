from django.db.models import Q
from django.shortcuts import render

from .models import FAQ, ErrorCode


def faq_list(request):
    faqs = FAQ.objects.filter(is_active=True)
    query = request.GET.get("q", "").strip()[:100]
    category = request.GET.get("category", "").strip()
    if query:
        faqs = faqs.filter(Q(question__icontains=query) | Q(answer__icontains=query) | Q(keywords__icontains=query))
    if category in FAQ.Category.values:
        faqs = faqs.filter(category=category)
    return render(request, "faqs/faq_list.html", {
        "faqs": faqs, "query": query, "selected_category": category, "categories": FAQ.Category.choices,
    })


def error_codes(request):
    codes = ErrorCode.objects.all()
    query = request.GET.get("q", "").strip()[:60]
    if query:
        filters = Q(name__icontains=query) | Q(meaning__icontains=query) | Q(common_causes__icontains=query)
        if query.isdigit():
            filters |= Q(code=int(query))
        codes = codes.filter(filters)
    return render(request, "faqs/error_codes.html", {"codes": codes, "query": query})
