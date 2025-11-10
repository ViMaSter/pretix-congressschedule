from django.urls import path
from .api import CongressScheduleView

urlpatterns = [
    path(
        'api/v1/event/<str:organizer>/<str:event>/schedule.xml',
        CongressScheduleView.as_view(),
        name='schedule-xml',
    ),
]