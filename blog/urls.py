from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),

    path('article/<slug:slug>/',views.article_detail,name='article_detail'),

    path('category/<slug:slug>/',views.category_detail,name='category_detail'),

    
    path('search/',views.search_articles,name='search_articles'),
    path('newsletter/subscribe/', views.subscribe_newsletter, name='subscribe_newsletter'),

    path("newsletter/unsubscribe/<str:token>/",views.unsubscribe_newsletter,name="unsubscribe_newsletter"),

    path("donate/", views.donate, name="donate"),

    path("donate/callback/", views.donation_callback, name="donation_callback"),

    
]
]
