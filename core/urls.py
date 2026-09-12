from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .views import brand, creator, public

urlpatterns = [
    path("", public.home, name="home"),

    path("signup/", public.signup, name="signup"),
    path("login/", auth_views.LoginView.as_view(
        template_name="auth/login.html", redirect_authenticated_user=True,
    ), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("app/", views.dashboard, name="dashboard"),

    path("app/discover/", brand.discover, name="discover"),
    path("app/creators/<int:pk>/", brand.creator_detail, name="creator_detail"),
    path("app/campaigns/", brand.campaigns, name="campaigns"),
    path("app/campaigns/new/", brand.campaign_new, name="campaign_new"),
    path("app/campaigns/<int:pk>/", brand.campaign_detail, name="campaign_detail"),
    path("app/analytics/", brand.analytics, name="analytics"),

    path("app/deals/", creator.deals, name="creator_deals"),
    path("app/deals/<int:pk>/", creator.deal_detail, name="creator_deal_detail"),
    path("app/earnings/", creator.earnings, name="creator_earnings"),
]
