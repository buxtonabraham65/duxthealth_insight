
from django.contrib import admin
from django import forms
from django.db import transaction
from django.utils import timezone

from tinymce.widgets import TinyMCE

from .models import (
    Category,
    Tag,
    Author,
    MedicalReviewer,
    Article,
    ArticleView,
    NewsletterSubscriber,
    ArticleNotification,
    Donation,
)

from .newsletter import send_article_notification


# ==========================================
# RICH TEXT ARTICLE FORM
# ==========================================

class ArticleAdminForm(forms.ModelForm):

    body = forms.CharField(
        widget=TinyMCE(
            attrs={
                "cols": 80,
                "rows": 30,
            }
        )
    )

    class Meta:
        model = Article
        fields = "__all__"


# ==========================================
# CATEGORY ADMINISTRATION
# ==========================================

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "slug",
        "is_active",
        "created_at",
    )

    list_filter = ("is_active",)
    search_fields = ("name", "description")

    prepopulated_fields = {
        "slug": ("name",)
    }


# ==========================================
# TAG ADMINISTRATION
# ==========================================

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):

    list_display = ("name", "slug")
    search_fields = ("name",)

    prepopulated_fields = {
        "slug": ("name",)
    }


# ==========================================
# AUTHOR ADMINISTRATION
# ==========================================

@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):

    list_display = (
        "display_name",
        "designation",
        "email",
        "is_active",
    )

    list_filter = ("is_active",)

    search_fields = (
        "display_name",
        "designation",
        "email",
    )


# ==========================================
# MEDICAL REVIEWER ADMINISTRATION
# ==========================================

@admin.register(MedicalReviewer)
class MedicalReviewerAdmin(admin.ModelAdmin):

    list_display = (
        "full_name",
        "professional_title",
        "qualifications",
        "is_active",
    )

    list_filter = ("is_active",)

    search_fields = (
        "full_name",
        "professional_title",
        "qualifications",
    )


# ==========================================
# ARTICLE ADMINISTRATION
# ==========================================

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):

    form = ArticleAdminForm

    list_display = (
        "title",
        "category",
        "author",
        "status",
        "medically_reviewed",
        "featured",
        "published_at",
        "views",
    )

    list_filter = (
        "status",
        "category",
        "featured",
        "medically_reviewed",
        "published_at",
    )

    search_fields = (
        "title",
        "subtitle",
        "excerpt",
        "body",
        "references",
    )

    prepopulated_fields = {
        "slug": ("title",)
    }

    filter_horizontal = ("tags",)

    date_hierarchy = "created_at"

    readonly_fields = (
        "views",
        "created_at",
        "updated_at",
    )

    fieldsets = (

        ("Article Information", {
            "fields": (
                "title",
                "slug",
                "subtitle",
                "excerpt",
                "body",
            )
        }),

        ("Images", {
            "fields": (
                "cover_image",
                "cover_image_caption",
            )
        }),

        ("Categories and Tags", {
            "fields": (
                "category",
                "tags",
            )
        }),

        ("Author and Medical Review", {
            "fields": (
                "author",
                "reviewer",
                "medically_reviewed",
                "review_notes",
            )
        }),

        ("Publishing", {
            "fields": (
                "status",
                "featured",
                "scheduled_for",
                "published_at",
            )
        }),

        ("References", {
            "fields": (
                "references",
            )
        }),

        ("SEO Settings", {
            "fields": (
                "meta_title",
                "meta_description",
            ),
            "classes": ("collapse",),
        }),

        ("Statistics", {
            "fields": (
                "views",
                "created_at",
                "updated_at",
            ),
            "classes": ("collapse",),
        }),
    )

    def save_model(self, request, obj, form, change):

        was_public = False

        if obj.pk:

            previous = Article.objects.filter(
                pk=obj.pk
            ).first()

            if previous:
                was_public = (
                    previous.status == Article.Status.PUBLISHED
                    and previous.published_at is not None
                    and previous.published_at <= timezone.now()
                )

        super().save_model(request, obj, form, change)

        if obj.is_public and not was_public:

            article_id = obj.pk

            transaction.on_commit(
                lambda: send_article_notification(
                    request,
                    article_id
                )
            )


# ==========================================
# ARTICLE VIEW ADMINISTRATION
# ==========================================

@admin.register(ArticleView)
class ArticleViewAdmin(admin.ModelAdmin):

    list_display = (
        "article",
        "viewed_at",
    )

    list_filter = ("viewed_at",)

    search_fields = ("article__title",)

    readonly_fields = (
        "article",
        "viewed_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# ==========================================
# NEWSLETTER ADMINISTRATION
# ==========================================

@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):

    list_display = (
        "email",
        "active",
        "consent_given",
        "subscribed_at",
    )

    list_filter = (
        "active",
        "consent_given",
    )

    search_fields = ("email",)


# ==========================================
# CUSTOM ADMIN BRANDING
# ==========================================

admin.site.site_header = "DuxtHealth Insights"
admin.site.site_title = "DuxtHealth Publisher"
admin.site.index_title = "Content Management Dashboard"


# ==========================================
# NEWSLETTER NOTIFICATION
# ==========================================

@admin.register(ArticleNotification)
class ArticleNotificationAdmin(admin.ModelAdmin):

    list_display = (
        "status",
        "article",
        "recipient_count",
        "sent_at",
        "error_message",
        "created_at",
    )

    list_filter = (
        "status",
        "article",
    )

    search_fields = ("status",)


# ==========================================
# DUXTHEALTH DONATIONS ADMIN
# ==========================================

@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):

    list_display = (
        "donor_name",
        "donor_email",
        "amount",
        "currency",
        "status",
        "created_at",
        "paid_at",
    )

    list_filter = (
        "status",
        "currency",
        "created_at",
    )

    search_fields = (
        "donor_name",
        "donor_email",
        "reference",
        "paystack_transaction_id",
    )

    readonly_fields = (
        "donor_name",
        "donor_email",
        "message",
        "amount",
        "currency",
        "reference",
        "paystack_transaction_id",
        "status",
        "paid_at",
        "created_at",
        "updated_at",
    )

    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
