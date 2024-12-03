from django.http import JsonResponse
from .models import Student, Subject, Attendance
import requests
import datetime

def fetch_and_update_data(request):
    # Fetch data from Linways API
    api_key = 'CQTnCjhviK'
    api_secret_key = 'LEJ8TzUjzdR6iGU2G'
    api_endpoint = 'https://uatleadv4.linways.com/lin-api/v1/academics/student/get-student-data-for-attendance/'
    today_date = datetime.date.today().strftime('%Y-%m-%d')

    request_body = {'date': today_date}
    headers = {'Apikey': api_key, 'Apisecretkey': api_secret_key}

    response = requests.post(api_endpoint, json=request_body, headers=headers)
    if response.status_code != 200:
        return JsonResponse({'error': f"Failed to fetch data: {response.text}"}, status=500)

    data = response.json()

    # Clear existing data
    Student.objects.all().delete()
    Subject.objects.all().delete()
    Attendance.objects.all().delete()

    # Insert new data
    for student_data in data['data']['studentDetails']:
        student_email = student_data['studentEmail'] or f"{student_data['studentID']}@default.email"

        student = Student.objects.create(
            student_email=student_email,
            student_id=student_data['studentID'],
            student_name=student_data['studentName'],
            student_program_id=student_data.get('studentProgramId'),
            batch_name=student_data.get('batchName')
        )

        for hour_data in student_data['Hour']:
            subject, _ = Subject.objects.get_or_create(
                subject_id=hour_data['subjectId'],
                defaults={
                    'subject_name': hour_data['subjectName'],
                    'cluster_name': hour_data['clusterName'],
                    'cluster_id': hour_data['clusterId']
                }
            )

            Attendance.objects.create(
                student_email=student,
                date=student_data['date'],
                subject_id=subject,
                from_time=hour_data['fromTime'],
                to_time=hour_data['toTime'],
                hour=hour_data['hour'],
                is_present=hour_data['isPresent'] == '1',
                staff_id=hour_data['staffId'],
                staff_name=hour_data['staffName'],
                staff_email=hour_data['staffEmail'],
                time_table_id=hour_data['timeTableId']
            )

    return JsonResponse({'message': 'Data fetched and updated successfully'})

