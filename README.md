# Attendance-System-Lead

## Steps for Deployment

1. Install pip.
```
sudo apt-get install python3-pip
```
2. Clone This Repository
```
git clone <Repo URL>
```
3. Install Required Libraries.
```
pip install -r requirements.txt
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
