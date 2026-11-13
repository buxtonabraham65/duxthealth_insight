from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.text import slugify
import uuid


# ==========================================
# 1. ARTICLE CATEGORIES
# ==========================================

class Category(models.Model):

    name = models.CharField(max_length=100, unique=True)

    slug = models.SlugField(
        max_length=120,
        unique=True,
        blank=True
    )

    description = models.TextField(blank=True)

    image = models.ImageField(
        upload_to="categories/",
        blank=True,
        null=True
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            candidate = base_slug
            counter = 1

            while Category.objects.filter(
                slug=candidate
            ).exclude(pk=self.pk).exists():
                candidate = f"{base_slug}-{counter}"
                counter += 1

            self.slug = candidate

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# ==========================================
# 2. ARTICLE TAGS
# ==========================================

class Tag(models.Model):

    name = models.CharField(max_length=50, unique=True)

    slug = models.SlugField(
        max_length=60,
        unique=True,
        blank=True
    )

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            candidate = base_slug
            counter = 1

            while Tag.objects.filter(
                slug=candidate
            ).exclude(pk=self.pk).exists():
                candidate = f"{base_slug}-{counter}"
                counter += 1

            self.slug = candidate

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# ==========================================
# 3. AUTHORS
# ==========================================

class Author(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="blog_author_profile"
    )

    display_name = models.CharField(max_length=150)

    designation = models.CharField(
        max_length=150,
        blank=True
    )

    biography = models.TextField(blank=True)

    profile_image = models.ImageField(
        upload_to="authors/",
        blank=True,
        null=True
    )

    email = models.EmailField(blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["display_name"]

    def __str__(self):
        return self.display_name


# ==========================================
# 4. MEDICAL REVIEWERS
# ==========================================

class MedicalReviewer(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="blog_reviewer_profile"
    )

    full_name = models.CharField(max_length=150)

    professional_title = models.CharField(
        max_length=150
    )

    qualifications = models.CharField(
        max_length=250,
        blank=True
    )

    biography = models.TextField(blank=True)

    profile_image = models.ImageField(
        upload_to="reviewers/",
        blank=True,
        null=True
    )

    email = models.EmailField(blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        return f"{self.full_name} - {self.professional_title}"


# ==========================================
# 5. MAIN ARTICLE MODEL
# ==========================================

class Article(models.Model):

    class Status(models.TextChoices):

        DRAFT = "draft", "Draft"

        REVIEW = "review", "Awaiting Medical Review"

        SCHEDULED = "scheduled", "Scheduled"

        PUBLISHED = "published", "Published"

        ARCHIVED = "archived", "Archived"


    # ARTICLE INFORMATION

    title = models.CharField(max_length=250)

    slug = models.SlugField(
        max_length=270,
        unique=True,
        blank=True
    )

    subtitle = models.CharField(
        max_length=300,
        blank=True
    )

    excerpt = models.TextField(
        max_length=500,
        help_text="Short introduction displayed on article cards."
    )

    body = models.TextField(
        help_text="Main article content."
    )


    # ARTICLE MEDIA

    cover_image = models.ImageField(
        upload_to="articles/covers/%Y/%m/",
        blank=True,
        null=True
    )

    cover_image_caption = models.CharField(
        max_length=250,
        blank=True
    )


    # ARTICLE CLASSIFICATION

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="articles"
    )

    tags = models.ManyToManyField(
        Tag,
        blank=True,
        related_name="articles"
    )


    # AUTHORSHIP

    author = models.ForeignKey(
        Author,
        on_delete=models.PROTECT,
        related_name="articles"
    )

    reviewer = models.ForeignKey(
        MedicalReviewer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_articles"
    )


    # EDITORIAL MANAGEMENT

    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.DRAFT
    )

    featured = models.BooleanField(default=False)

    medically_reviewed = models.BooleanField(default=False)

    review_notes = models.TextField(blank=True)


    # REFERENCES

    references = models.TextField(
        blank=True,
        help_text="Add reliable sources and reference URLs, one per line."
    )


    # SEARCH ENGINE OPTIMISATION

    meta_title = models.CharField(
        max_length=250,
        blank=True
    )

    meta_description = models.CharField(
        max_length=320,
        blank=True
    )


    # PUBLICATION MANAGEMENT

    scheduled_for = models.DateTimeField(
        null=True,
        blank=True
    )

    published_at = models.DateTimeField(
        null=True,
        blank=True
    )


    # ARTICLE STATISTICS

    views = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)


    class Meta:

        ordering = ["-published_at", "-created_at"]

        indexes = [
            models.Index(
                fields=["status", "published_at"]
            ),
            models.Index(
                fields=["featured", "status"]
            ),
        ]


    def save(self, *args, **kwargs):

        if not self.slug:

            base_slug = slugify(self.title) or "article"

            candidate = base_slug

            counter = 1

            while Article.objects.filter(
                slug=candidate
            ).exclude(pk=self.pk).exists():

                candidate = f"{base_slug}-{counter}"

                counter += 1

            self.slug = candidate

        super().save(*args, **kwargs)


    @property
    def is_public(self):

        return (
            self.status == self.Status.PUBLISHED
            and self.published_at is not None
            and self.published_at <= timezone.now()
        )


    def __str__(self):
        return self.title


# ==========================================
# 6. ARTICLE VIEW TRACKING
# ==========================================

class ArticleView(models.Model):

    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name="article_views"
    )

    viewed_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-viewed_at"]

    def __str__(self):
        return f"View: {self.article.title}"


# ==========================================
# 7. NEWSLETTER SUBSCRIBERS
# ==========================================

class NewsletterSubscriber(models.Model):

    email = models.EmailField(unique=True)

    active = models.BooleanField(default=True)

    consent_given = models.BooleanField(default=False)

    subscribed_at = models.DateTimeField(
        auto_now_add=True
    )

    unsubscribed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        ordering = ["-subscribed_at"]

    def __str__(self):
        return self.email

# ==========================================
# 8. ARTICLE NEWSLETTER NOTIFICATIONS
# ==========================================

class ArticleNotification(models.Model):

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    article = models.OneToOneField(
        Article,
        on_delete=models.CASCADE,
        related_name="newsletter_notification"
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING
    )

    recipient_count = models.PositiveIntegerField(default=0)

    sent_at = models.DateTimeField(
        null=True,
        blank=True
    )

    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Notification: {self.article.title} ({self.status})"


# ==========================================
# 9. DUXTHEALTH DONATIONS
# ==========================================

class Donation(models.Model):

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCESSFUL = "successful", "Successful"
        FAILED = "failed", "Failed"

    # DONOR INFORMATION

    donor_name = models.CharField(
        max_length=150
    )

    donor_email = models.EmailField()

    message = models.TextField(
        blank=True
    )

    # DONATION INFORMATION

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    currency = models.CharField(
        max_length=3,
        default="GHS"
    )

    # PAYMENT REFERENCE

    reference = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )

    paystack_transaction_id = models.CharField(
        max_length=100,
        blank=True
    )

    # PAYMENT STATUS

    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PENDING
    )

    paid_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # RECORD MANAGEMENT

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["status", "created_at"]
            ),
        ]

    def __str__(self):
        return (
            f"{self.donor_name} - "
            f"{self.currency} {self.amount} "
            f"({self.status})"
        )


