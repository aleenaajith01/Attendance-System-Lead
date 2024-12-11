from django.urls import path
from . import views
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('fetch-update-data/', views.fetch_and_update_data, name='fetch_update_data'),
    path('send-attendance/', views.send_attendance_data, name='send_attendance'),
    path('trigger-attendance-requests/', views.trigger_attendance_requests, name='trigger_attendance_requests')
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)