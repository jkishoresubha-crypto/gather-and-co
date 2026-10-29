from django.conf import settings
from django.shortcuts import get_object_or_404, redirect, render

from core.ratelimit import is_rate_limited

from .forms import SupportTicketForm
from .models import SupportTicket


def support(request):
    initial = {}
    if request.user.is_authenticated:
        initial = {"name": request.user.get_full_name() or request.user.username, "email": request.user.email}
    form = SupportTicketForm(request.POST or None, initial=initial)
    status = 200
    if request.method == "POST":
        if is_rate_limited(request, "ticket", settings.TICKET_RATE_LIMIT, window=600):
            form.add_error(None, "Too many tickets were submitted from your connection (429). Please wait a few minutes.")
            status = 429
        elif form.is_valid():
            ticket = form.save()
            # Remember the reference in the session so only this visitor can see the confirmation.
            request.session["last_ticket"] = ticket.reference
            return redirect("support:submitted", reference=ticket.reference)
        else:
            status = 400
    return render(request, "support/support.html", {"form": form}, status=status)


def submitted(request, reference):
    if request.session.get("last_ticket") != reference:
        return redirect("support:support")
    ticket = get_object_or_404(SupportTicket, reference=reference)
    return render(request, "support/submitted.html", {"ticket": ticket})
