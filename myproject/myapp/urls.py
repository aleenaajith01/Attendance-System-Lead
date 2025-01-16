from django.urls import path
from . import views
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('fetch-update-data/', views.fetch_and_update_data, name='fetch_update_data'),
    path('send-attendance/', views.send_attendance_data, name='send_attendance'),
    path('trigger-attendance-requests/', views.trigger_attendance_requests, name='trigger_attendance_requests'),
    path('fetch-and-capture-images/', views.fetch_and_capture_images, name='fetch_and_capture_images'),
    path('take_attendance/', views.take_attendance, name='take_attendance'),
    path('data_for_frontend_dashboard/', views.data_for_frontend_dashboard, name='data_for_frontend_dashboard'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)