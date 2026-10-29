from django.urls import path

from . import views

app_name = "assistant"
urlpatterns = [
    path("chat/", views.chat, name="chat"),
    path("ticket/", views.create_ticket, name="ticket"),
    path("feedback/", views.feedback, name="feedback"),
]
