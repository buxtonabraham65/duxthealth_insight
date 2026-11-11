from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.db.models import F
from django.core.paginator import Paginator
from .models import Article, Category, ArticleView, NewsletterSubscriber, ArticleNotification
from django.db.models import Q

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.contrib import messages
from django.views.decorators.http import require_POST

from django.core.mail import send_mail
from django.conf import settings
from django.core import signing
from django.urls import reverse
from django.db import transaction
from django.views.decorators.http import require_http_methods

from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags


def home(request):

    now = timezone.now()

    # Only display articles that are officially published
    # and whose publication date has arrived.

    published_articles = Article.objects.filter(
        status=Article.Status.PUBLISHED,
        published_at__lte=now
    ).select_related(
        "category",
        "author",
        "reviewer"
    ).prefetch_related("tags")

    # Featured article
    featured_article = published_articles.filter(
        featured=True
    ).order_by("-published_at").first()

    # Latest publications
    latest_articles = published_articles.order_by(
        "-published_at"
    )[:9]

    # Popular articles
    popular_articles = published_articles.order_by(
        "-views",
        "-published_at"
    )[:4]

    # Active categories
    categories = Category.objects.filter(
        is_active=True
    ).order_by("name")

    context = {
        "site_name": "DuxtHealth Insights",
        "tagline": "Knowledge. Prevention. Better Health.",

        "featured_article": featured_article,
        "latest_articles": latest_articles,
        "popular_articles": popular_articles,
        "categories": categories,
    }

    return render(
        request,
        "blog/home.html",
        context
    )


def article_detail(request, slug):
    now = timezone.now()

    article = get_object_or_404(
        Article.objects.select_related(
            'category',
            'author',
            'reviewer'
        ).prefetch_related('tags'),
        slug=slug,
        status='published',
        published_at__lte=now
    )

    # Record the article view
    Article.objects.filter(pk=article.pk).update(
        views=F('views') + 1
    )

    ArticleView.objects.create(article=article)

    # Refresh the view count
    article.refresh_from_db()

    # Find related articles in the same category
    related_articles = Article.objects.filter(
        status='published',
        published_at__lte=now,
        category=article.category
    ).exclude(
        pk=article.pk
    ).select_related(
        'category',
        'author'
    ).order_by('-published_at')[:4]

    context = {
        'article': article,
        'related_articles': related_articles,
    }

    return render(
        request,
        'blog/article_detail.html',
        context
    )

#Categories view

def category_detail(request, slug):
    now = timezone.now()

    category = get_object_or_404(
        Category,
        slug=slug,
        is_active=True
    )

    article_list = Article.objects.filter(
        category=category,
        status='published',
        published_at__lte=now
    ).select_related(
        'category',
        'author',
        'reviewer'
    ).prefetch_related(
        'tags'
    ).order_by('-published_at')

    # Show 9 articles per page
    paginator = Paginator(article_list, 9)

    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'category': category,
        'page_obj': page_obj,
        'articles': page_obj.object_list,
    }

    return render(
        request,
        'blog/category_detail.html',
        context
    )

#Search

def search_articles(request):
    query = request.GET.get('q', '').strip()

    articles = Article.objects.none()

    if query:
        articles = Article.objects.filter(
            Q(title__icontains=query) |
            Q(subtitle__icontains=query) |
            Q(excerpt__icontains=query) |
            Q(body__icontains=query) |
            Q(category__name__icontains=query) |
            Q(tags__name__icontains=query),

            status='published',
            published_at__lte=timezone.now()
        ).select_related(
            'category',
            'author',
            'reviewer'
        ).prefetch_related(
            'tags'
        ).distinct().order_by('-published_at')

    paginator = Paginator(articles, 9)

    page_obj = paginator.get_page(
        request.GET.get('page')
    )

    context = {
        'query': query,
        'articles': page_obj.object_list,
        'page_obj': page_obj,
        'total_results': paginator.count,
    }

    return render(
        request,
        'blog/search_results.html',
        context
    )

#News letter

def send_newsletter_welcome_email(request, subscriber):
    """
    Send a welcome email containing a secure unsubscribe link.
    """

    token = signing.dumps(
        {
            "subscriber_id": subscriber.pk,
            "email": subscriber.email,
        },
        salt="duxthealth.newsletter.unsubscribe"
    )

    unsubscribe_path = reverse(
        "unsubscribe_newsletter",
        kwargs={"token": token}
    )

    unsubscribe_url = request.build_absolute_uri(unsubscribe_path)

    subject = "Welcome to DuxtHealth Insights!"

    message = f"""
Hello,

Thank you for subscribing to DuxtHealth Insights.

We are pleased to welcome you to our health education community.

You will receive updates, health education articles,
and informative publications from DuxtHealth Insights.

We are committed to making reliable health information
more accessible to everyone.

If you no longer wish to receive these emails, you can
unsubscribe using the link below:

{unsubscribe_url}

Thank you for being part of our community.

DuxtHealth Insights
Making Healthcare Accessible to Everyone, Everywhere.
"""

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [subscriber.email],
        fail_silently=False
    )

@require_POST
def subscribe_newsletter(request):

    email = request.POST.get('email', '').strip().lower()
    consent = request.POST.get('consent')

    if not email:
        messages.error(request, "Please enter your email address.")
        return redirect('/#newsletter')

    try:
        validate_email(email)
    except ValidationError:
        messages.error(request, "Please enter a valid email address.")
        return redirect('/#newsletter')

    if consent not in ('on', 'true', '1', 'yes'):
        messages.error(
            request,
            "Please give your consent before subscribing."
        )
        return redirect('/#newsletter')

    subscriber = NewsletterSubscriber.objects.filter(
        email__iexact=email
    ).first()

    if subscriber and subscriber.active:
        messages.info(
            request,
            "This email address is already subscribed."
        )
        return redirect('/#newsletter')

    if subscriber:
        subscriber.active = True
        subscriber.consent_given = True
        subscriber.subscribed_at = timezone.now()
        subscriber.unsubscribed_at = None
        subscriber.save()

    else:
        subscriber = NewsletterSubscriber.objects.create(
            email=email,
            active=True,
            consent_given=True,
            subscribed_at=timezone.now()
        )

    # The subscriber is saved before attempting email delivery.
    try:
        send_newsletter_welcome_email(request, subscriber)

        messages.success(
            request,
            "Thank you for subscribing! Your welcome email has been sent."
        )

    except Exception:
        messages.warning(
            request,
            "Your subscription was saved successfully, but we could not "
            "send your welcome email. Please try again later."
        )

    return redirect('/#newsletter')

@require_http_methods(["GET", "POST"])
def unsubscribe_newsletter(request, token):

    try:
        data = signing.loads(
            token,
            salt="duxthealth.newsletter.unsubscribe"
        )

    except signing.BadSignature:
        return render(
            request,
            "blog/newsletter_unsubscribe.html",
            {"status": "invalid"},
            status=400
        )

    subscriber = NewsletterSubscriber.objects.filter(
        pk=data.get("subscriber_id"),
        email=data.get("email")
    ).first()

    if not subscriber:
        return render(
            request,
            "blog/newsletter_unsubscribe.html",
            {"status": "invalid"},
            status=400
        )

    if request.method == "POST":

        if subscriber.active:
            subscriber.active = False
            subscriber.unsubscribed_at = timezone.now()
            subscriber.save(
                update_fields=["active", "unsubscribed_at"]
            )

        return render(
            request,
            "blog/newsletter_unsubscribe.html",
            {"status": "success"}
        )

    if not subscriber.active:
        return render(
            request,
            "blog/newsletter_unsubscribe.html",
            {"status": "already_unsubscribed"}
        )

    return render(
        request,
        "blog/newsletter_unsubscribe.html",
        {
            "status": "confirm",
            "subscriber": subscriber,
            "token": token,
        }
    )