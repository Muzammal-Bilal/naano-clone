"""Forms for signup and campaign creation."""

from django import forms
from django.contrib.auth.models import User

from .models import Brand, Campaign, Creator, Topic

FIELD_CLASS = (
    "w-full rounded-2xl border border-black/10 px-4 py-3 text-[15px] "
    "focus:outline-none focus:ring-2 focus:ring-[#2E90FA]/40 focus:border-[#2E90FA]"
)


class SignupForm(forms.Form):
    """One form, two outcomes: a Brand row or a Creator row."""

    ROLE_CHOICES = [("brand", "I'm a brand"), ("creator", "I'm a creator")]

    role = forms.ChoiceField(choices=ROLE_CHOICES, initial="brand")
    full_name = forms.CharField(max_length=80)
    email = forms.EmailField()
    password = forms.CharField(min_length=8, widget=forms.PasswordInput)
    # Company for brands, LinkedIn headline for creators.
    context = forms.CharField(max_length=120, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != "role":
                field.widget.attrs["class"] = FIELD_CLASS

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with that email already exists.")
        return email

    def save(self):
        data = self.cleaned_data
        name_parts = data["full_name"].split(" ", 1)

        user = User.objects.create_user(
            username=data["email"],
            email=data["email"],
            password=data["password"],
            first_name=name_parts[0],
            last_name=name_parts[1] if len(name_parts) > 1 else "",
        )

        if data["role"] == "creator":
            Creator.objects.create(
                user=user,
                display_name=data["full_name"],
                headline=data["context"] or "B2B creator",
                avatar_url=f"https://api.dicebear.com/7.x/initials/svg?seed={data['full_name']}",
                followers=1200,
                median_views=600,
                price_per_post=80,
            )
        else:
            Brand.objects.create(
                user=user,
                company_name=data["context"] or data["full_name"],
                wallet_balance=5000,
            )
        return user


class CampaignForm(forms.ModelForm):
    """Step one of the brief builder. The generated copy is filled in after."""

    class Meta:
        model = Campaign
        fields = ["name", "objective", "pricing_model", "budget",
                  "product_description", "landing_url"]
        widgets = {"product_description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = FIELD_CLASS
