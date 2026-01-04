from django.urls import path
from .api import CongressScheduleXMLView, CongressScheduleJSONView, HackertoursMarkdownView

urlpatterns = [
    path(
        'api/v1/event/<str:organizer>/<str:event>/schedule.xml',
        CongressScheduleXMLView.as_view(),
        name='schedule-xml',
    ),
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