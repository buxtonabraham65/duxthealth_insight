from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags

from .models import ArticleNotification, NewsletterSubscriber


def send_article_notification(request, article_id):

    notification = None

    try:
        # Retrieve the article.
        from .models import Article

        article = Article.objects.get(
            pk=article_id,
            status=Article.Status.PUBLISHED,
            published_at__lte=timezone.now()
        )

        # Prevent duplicate notifications.
        notification, created = ArticleNotification.objects.get_or_create(
            article=article
        )

        if not created and notification.status == ArticleNotification.Status.SENT:
            return

        notification.status = ArticleNotification.Status.PENDING
        notification.error_message = ""
        notification.save()

        # Retrieve active subscribers who gave consent.
        subscribers = NewsletterSubscriber.objects.filter(
            active=True,
            consent_given=True
        )

        recipient_emails = list(
            subscribers.values_list("email", flat=True)
        )

        if not recipient_emails:
            notification.status = ArticleNotification.Status.SENT
            notification.recipient_count = 0
            notification.sent_at = timezone.now()
            notification.save()
            return

        # Create the public article URL.
        article_path = reverse(
            "article_detail",
            kwargs={"slug": article.slug}
        )

        article_url = request.build_absolute_uri(article_path)

        subject = f"New from DuxtHealth Insights: {article.title}"

        excerpt = article.excerpt or article.subtitle

        plain_message = f"""
Hello,

A new article has been published on DuxtHealth Insights.

{article.title}

{excerpt}

Read the full article here:
{article_url}

Thank you for being part of the DuxtHealth Insights community.

DuxtHealth Insights
Making Healthcare Accessible to Everyone, Everywhere.
"""

        html_message = f"""
<html>
<body style="font-family: Arial, sans-serif; color: #333;">
    <div style="max-width: 600px; margin: auto; padding: 25px;">

        <h2 style="color: #005B55;">
            DuxtHealth Insights
        </h2>

        <p>Hello,</p>

        <p>
            A new article has been published on
            <strong>DuxtHealth Insights</strong>.
        </p>

        <h2 style="color: #005B55;">
            {article.title}
        </h2>

        <p>{excerpt}</p>

        <p>
            <a href="{article_url}"
               style="background: #005B55; color: white;
                      padding: 13px 22px; text-decoration: none;
                      border-radius: 6px; display: inline-block;">
                Read Article
            </a>
        </p>

        <p>
            Thank you for being part of our community.
        </p>

        <p>
            DuxtHealth Insights<br>
            Making Healthcare Accessible to Everyone, Everywhere.
        </p>

    </div>
</body>
</html>
"""

        email = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[settings.DEFAULT_FROM_EMAIL],
            bcc=recipient_emails
        )

        email.attach_alternative(html_message, "text/html")

        email.send(fail_silently=False)

        notification.status = ArticleNotification.Status.SENT
        notification.recipient_count = len(recipient_emails)
        notification.sent_at = timezone.now()
        notification.error_message = ""
        notification.save()

    except Exception as error:

        if notification is not None:
            notification.status = ArticleNotification.Status.FAILED
            notification.error_message = str(error)[:2000]
            notification.save()

        raise