"""Creator side: incoming deals, drafts, earnings."""

from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from core.models import Booking, Transaction


def creator_required(view):
    @wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        creator = getattr(request.user, "creator", None)
        if creator is None:
            raise Http404("This page is for creator accounts.")
        return view(request, creator, *args, **kwargs)
    return wrapper


@creator_required
def deals(request, creator):
    bookings = (
        Booking.objects
        .filter(creator=creator)
        .select_related("campaign", "campaign__brand")
        .prefetch_related("metrics")
    )
    return render(request, "app/deals.html", {
        "invited": [b for b in bookings if b.status == Booking.Status.INVITED],
        "active": [b for b in bookings if b.status in (
            Booking.Status.ACCEPTED, Booking.Status.DRAFT,
            Booking.Status.SCHEDULED, Booking.Status.LIVE,
        )],
        "closed": [b for b in bookings if b.status in (
            Booking.Status.COMPLETED, Booking.Status.DECLINED,
        )],
    })


@creator_required
def deal_detail(request, creator, pk):
    booking = get_object_or_404(
        Booking.objects.select_related("campaign", "campaign__brand"),
        pk=pk, creator=creator,
    )

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "accept" and booking.status == Booking.Status.INVITED:
            booking.status = Booking.Status.ACCEPTED
            messages.success(request, "Deal accepted. Draft your post when ready.")
        elif action == "decline" and booking.status == Booking.Status.INVITED:
            booking.status = Booking.Status.DECLINED
            messages.info(request, "Deal declined.")
        elif action == "submit_draft":
            booking.draft_content = request.POST.get("draft_content", "").strip()
            booking.status = Booking.Status.DRAFT
            messages.success(request, "Draft sent to the brand for review.")
        booking.save()
        return redirect("creator_deal_detail", pk=booking.pk)

    return render(request, "app/deal_detail.html", {"booking": booking})


@creator_required
def earnings(request, creator):
    payouts = Transaction.objects.filter(
        user=creator.user, kind=Transaction.Kind.PAYOUT
    ).select_related("booking__campaign")

    pending = Booking.objects.filter(
        creator=creator,
        status__in=[Booking.Status.ACCEPTED, Booking.Status.DRAFT,
                    Booking.Status.SCHEDULED, Booking.Status.LIVE],
    ).aggregate(total=Sum("price"))["total"] or 0

    return render(request, "app/earnings.html", {
        "payouts": payouts,
        "paid_total": payouts.aggregate(total=Sum("amount"))["total"] or 0,
        "pending_total": pending,
    })
