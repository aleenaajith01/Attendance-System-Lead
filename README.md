# Attendance-System-Lead

## Steps for Deployment

1. Clone This Repository
```
git clone <Repo URL>
```
2. Install Required Libraries.
```
pip install -m requirements.txt
```
3. Run Django Server.
```
python manage.py runserver
```
4. Run Celery Server.
```
celery -A myproject worker --loglevel=info --concurrency=18
```
5. Run Scheduler.
```
python scheduler.py
```
