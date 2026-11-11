from django.contrib import admin
from .models import (
    Category,
    Tag,
    Author,
    MedicalReviewer,
    Article,
    ArticleView,
    NewsletterSubscriber,
    ArticleNotification,
)

from django.db import transaction
from django.utils import timezone

from .newsletter import send_article_notification


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

    ###
    def save_model(self, request, obj, form, change):

        was_public = False

        # Check whether the article was already published.
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

        # Save the article first.
        super().save_model(request, obj, form, change)

        # Notify subscribers only when the article becomes public.
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
