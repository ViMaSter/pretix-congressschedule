from django.urls import path
from .api import CongressScheduleJSONView, HackertoursMarkdownView

urlpatterns = [
    path(
        'api/v1/event/<str:organizer>/<str:event>/schedule.json',
        CongressScheduleJSONView.as_view(),
        name='schedule-json',
    ),
    path(
        'api/v1/event/<str:organizer>/<str:event>/schedule.md',
        HackertoursMarkdownView.as_view(),
        name='schedule-md',
    ),
]