"""View layer, split by audience: public marketing, brand app, creator app."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from . import brand, public


@login_required
def dashboard(request):
    """Send each side of the marketplace to its own home screen."""
    if hasattr(request.user, "creator"):
        return redirect("creator_deals")
    return redirect("discover")


__all__ = ["brand", "public", "dashboard"]
