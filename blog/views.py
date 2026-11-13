from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.db.models import F
from django.core.paginator import Paginator
from .models import Article, Category, ArticleView, NewsletterSubscriber, ArticleNotification, Donation
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

from decimal import Decimal, InvalidOperation
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

import uuid

import requests

import logging

logger = logging.getLogger(__name__)


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

# ==========================================
# PAYSTACK PAYMENT INITIALIZATION
# ==========================================





# ==========================================
# DUXTHEALTH DONATION PROCESSING
# ==========================================

def donate(request):

    if request.method == "POST":

        donor_name = request.POST.get(
            "donor_name", ""
        ).strip()

        donor_email = request.POST.get(
            "donor_email", ""
        ).strip()

        amount_input = request.POST.get(
            "amount", ""
        ).strip()

        message = request.POST.get(
            "message", ""
        ).strip()

        errors = []

        # VALIDATE DONOR NAME

        if not donor_name:
            errors.append("Please enter your full name.")

        elif len(donor_name) > 150:
            errors.append("Your name is too long.")

        # VALIDATE EMAIL

        if not donor_email:
            errors.append("Please enter your email address.")

        else:
            try:
                validate_email(donor_email)

            except ValidationError:
                errors.append("Please enter a valid email address.")

        # VALIDATE DONATION AMOUNT

        amount = None

        try:
            amount = Decimal(amount_input)

            if not amount.is_finite():
                errors.append("Please enter a valid donation amount.")

            elif amount < Decimal("1.00"):
                errors.append("The minimum donation is GHS 1.00.")

            elif amount > Decimal("1000000.00"):
                errors.append("The maximum donation is GHS 1,000,000.")

            elif amount.as_tuple().exponent < -2:
                errors.append(
                    "Donation amounts can have a maximum of two decimal places."
                )

        except (InvalidOperation, ValueError):
            errors.append("Please enter a valid donation amount.")

        # VALIDATE MESSAGE LENGTH

        if len(message) > 2000:
            errors.append("Your message is too long.")

        # RETURN VALIDATION ERRORS

        if errors:
            return render(
                request,
                "blog/donate.html",
                {
                    "form_errors": errors,
                    "form_data": request.POST,
                }
            )

        # CHECK PAYSTACK CONFIGURATION

        if not settings.PAYSTACK_SECRET_KEY:

            return render(
                request,
                "blog/donate.html",
                {
                    "payment_setup_pending": True,
                    "form_data": request.POST,
                }
            )

                # CREATE PENDING DONATION AND INITIALIZE PAYMENT

        try:
            donation = Donation.objects.create(
                donor_name=donor_name,
                donor_email=donor_email,
                amount=amount,
                currency="GHS",
                message=message,
                status=Donation.Status.PENDING,
            )

            # INITIALIZE PAYSTACK PAYMENT

            payment_data, payment_error = initialize_paystack_payment(
                request,
                donation
            )

        except Exception:
            logger.exception(
                "DUXTHEALTH DONATION PROCESSING ERROR"
            )
            raise

        # HANDLE PAYMENT INITIALIZATION FAILURE

        if not payment_data:

            return render(
                request,
                "blog/donate.html",
                {
                    "payment_initialization_error": payment_error,
                    "form_data": request.POST,
                }
            )
        # REDIRECT DONOR TO PAYSTACK CHECKOUT

        return redirect(
            payment_data["authorization_url"]
        )

    # DISPLAY DONATION PAGE

    return render(
        request,
        "blog/donate.html"
    )




# ==========================================
# PAYSTACK DONATION CALLBACK
# ==========================================

def donation_callback(request):

    reference = request.GET.get("reference", "").strip()

    if not reference:
        return render(
            request,
            "blog/donate.html",
            {
                "form_errors": [
                    "No payment reference was received. "
                    "Your donation could not be verified."
                ]
            }
        )

    # VALIDATE THE REFERENCE FORMAT

    try:
        donation_reference = uuid.UUID(reference)

    except (ValueError, TypeError, AttributeError):
        return render(
            request,
            "blog/donate.html",
            {
                "form_errors": [
                    "The payment reference is invalid."
                ]
            }
        )

    # FIND THE DONATION

    donation = Donation.objects.filter(
        reference=donation_reference
    ).first()

    if not donation:
        return render(
            request,
            "blog/donate.html",
            {
                "form_errors": [
                    "We could not find a donation matching this payment."
                ]
            }
        )

    # DO NOT VERIFY AGAIN IF ALREADY SUCCESSFUL

    if donation.status == Donation.Status.SUCCESSFUL:
        return render(
            request,
            "blog/donate.html",
            {
                "donation": donation,
                "payment_success": True,
            }
        )

    # CHECK PAYSTACK CONFIGURATION

    if not settings.PAYSTACK_SECRET_KEY:
        return render(
            request,
            "blog/donate.html",
            {
                "form_errors": [
                    "Payment verification is temporarily unavailable."
                ]
            }
        )

    # VERIFY PAYMENT DIRECTLY WITH PAYSTACK

    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.get(
            f"{settings.PAYSTACK_BASE_URL}/transaction/verify/{reference}",
            headers=headers,
            timeout=30,
        )

        response.raise_for_status()
        result = response.json()

    except (requests.RequestException, ValueError):
        return render(
            request,
            "blog/donate.html",
            {
                "form_errors": [
                    "We could not verify your payment at this time. "
                    "Your donation record has been preserved. "
                    "Please contact us if you have completed payment."
                ]
            }
        )

    # CHECK THE PAYSTACK RESPONSE

    if not isinstance(result, dict) or not result.get("status"):
        return render(
            request,
            "blog/donate.html",
            {
                "form_errors": [
                    "Paystack could not verify this transaction."
                ]
            }
        )

    payment = result.get("data")

    if not isinstance(payment, dict):
        return render(
            request,
            "blog/donate.html",
            {
                "form_errors": [
                    "Paystack returned an invalid payment record."
                ]
            }
        )

    # VERIFY THE TRANSACTION REFERENCE

    if payment.get("reference") != str(donation.reference):
        return render(
            request,
            "blog/donate.html",
            {
                "form_errors": [
                    "The payment reference does not match our donation record."
                ]
            }
        )

    # VERIFY PAYMENT STATUS

    if payment.get("status") != "success":
        return render(
            request,
            "blog/donate.html",
            {
                "form_errors": [
                    "Your payment has not been confirmed as successful. "
                    "Your donation record is still pending verification."
                ]
            }
        )

    # VERIFY THE PAYMENT AMOUNT

    try:
        paid_amount = int(payment.get("amount", 0))

    except (ValueError, TypeError):
        paid_amount = 0

    expected_amount = int(
        donation.amount * Decimal("100")
    )

    if paid_amount != expected_amount:
        return render(
            request,
            "blog/donate.html",
            {
                "form_errors": [
                    "The verified payment amount does not match your donation."
                ]
            }
        )

    # VERIFY CURRENCY

    if payment.get("currency") != donation.currency:
        return render(
            request,
            "blog/donate.html",
            {
                "form_errors": [
                    "The payment currency does not match your donation."
                ]
            }
        )

    # UPDATE DONATION SAFELY

    with transaction.atomic():

        donation = Donation.objects.select_for_update().get(
            pk=donation.pk
        )

        if donation.status == Donation.Status.PENDING:

            donation.status = Donation.Status.SUCCESSFUL

            donation.paystack_transaction_id = str(
                payment.get("id", "")
            )

            donation.paid_at = timezone.now()

            donation.save(
                update_fields=[
                    "status",
                    "paystack_transaction_id",
                    "paid_at",
                    "updated_at",
                ]
            )

    # DISPLAY PAYMENT SUCCESS

    return render(
        request,
        "blog/donate.html",
        {
            "donation": donation,
            "payment_success": True,
        }
    )


# ==========================================
# PAYSTACK PAYMENT INITIALIZATION
# ==========================================

def initialize_paystack_payment(request, donation):

    if not settings.PAYSTACK_SECRET_KEY:
        return None, "Paystack is not configured."

    amount_in_pesewas = int(
        donation.amount * Decimal("100")
    )

    callback_url = request.build_absolute_uri(
        reverse("donation_callback")
    )

    payload = {
        "email": donation.donor_email,
        "amount": amount_in_pesewas,
        "currency": donation.currency,
        "reference": str(donation.reference),
        "callback_url": callback_url,
        "metadata": {
            "donation_reference": str(donation.reference),
            "donor_name": donation.donor_name,
        },
    }

    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            f"{settings.PAYSTACK_BASE_URL}/transaction/initialize",
            json=payload,
            headers=headers,
            timeout=30,
        )

        response.raise_for_status()
        result = response.json()

        if (
            result.get("status")
            and result.get("data", {}).get("authorization_url")
        ):
            return result["data"], None

        return None, "Paystack could not initialize this payment."

    except requests.RequestException:
        return None, "Unable to connect to Paystack. Please try again."
