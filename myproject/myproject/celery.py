# from celery import Celery

# # Initialize Celery app
# app = Celery('myproject')

# # Set broker URL (using Redis in this example)
# app.conf.broker_url = 'redis://localhost:6379/0'

# # Look for tasks in installed apps
# app.autodiscover_tasks()

import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

app = Celery('myproject')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# Namespace 'CELERY_' means all celery-related configs are prefixed with 'CELERY_'.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Discover tasks in all installed apps
app.autodiscover_tasks()
