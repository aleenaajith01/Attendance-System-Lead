from django.http import JsonResponse
from .models import Student, Subject, Attendance
import requests
import datetime
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt
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


# @csrf_exempt
# def send_attendance_data(request):
#     if request.method == 'POST': 
#         try:
#             # Fetch attendance data using Django ORM
#             attendance_records = Attendance.objects.select_related('student_email', 'subject_id').all()

#             # Convert queryset into a list of dictionaries
#             attendance_data = []
#             for record in attendance_records:
#                 attendance_data.append({
#                     "studentEmail": record.student_email.student_email,
#                     "date": record.date.strftime('%Y-%m-%d'),
#                     "subjectId": record.subject_id.subject_id,
#                     "fromTime": record.from_time.strftime('%H:%M:%S'),
#                     "toTime": record.to_time.strftime('%H:%M:%S'),
#                     "hour": record.hour,
#                     "isPresent": record.is_present,
#                     "staffId": record.staff_id,
#                     "staffName": record.staff_name,
#                     "staffEmail": record.staff_email,
#                     "timeTableId": record.time_table_id
#                 })

#             # API endpoint for sending attendance
#             api_endpoint = 'https://uatleadv4.linways.com/lin-api/v1/academics/student/save-student-attendance/'
#             api_key = 'CQTnCjhviK'
#             api_secret_key = 'LEJ8TzUjzdR6iGU2G'

#             headers = { 
#                 'Apikey': api_key,
#                 'Apisecretkey': api_secret_key,
#                 'Content-Type': 'application/json'
#             }
            
#             payload = {
#             "currentHour": str(request.hour),
#             "studentDetails": attendance_data
#             }

#             # POST the attendance data to the API
#             response = requests.post(api_endpoint, json=payload, headers=headers)

#             if response.status_code == 200:
#                 return JsonResponse({"message": "Attendance data sent successfully.", "response": response.json()}, status=200)
#             else:
#                 return JsonResponse({"error": "Failed to send attendance data.", "details": response.text}, status=response.status_code)

#         except Exception as e:
#             return JsonResponse({"error": "An error occurred while processing the request.", "details": str(e)}, status=500)

#     return JsonResponse({"error": "Invalid request method. Use POST."}, status=405)

@csrf_exempt
def send_attendance_data(current_hour):
    
    try:
        # Fetch attendance data using Django ORM
        attendance_records = Attendance.objects.select_related('student_email', 'subject_id').all()

        # Convert queryset into a list of dictionaries
        attendance_data = []
        for record in attendance_records:
            attendance_data.append({
                "studentEmail": record.student_email.student_email,
                "date": record.date.strftime('%Y-%m-%d'),
                "subjectId": record.subject_id.subject_id,
                "fromTime": record.from_time.strftime('%H:%M:%S'),
                "toTime": record.to_time.strftime('%H:%M:%S'),
                "hour": record.hour,
                "isPresent": record.is_present,
                "staffId": record.staff_id,
                "staffName": record.staff_name,
                "staffEmail": record.staff_email,
                "timeTableId": record.time_table_id
            })

        # API endpoint for sending attendance
        api_endpoint = 'https://uatleadv4.linways.com/lin-api/v1/academics/student/save-student-attendance/'
        api_key = 'CQTnCjhviK'
        api_secret_key = 'LEJ8TzUjzdR6iGU2G'

        headers = { 
            'Apikey': api_key,
            'Apisecretkey': api_secret_key,
            'Content-Type': 'application/json'
        }
        
        payload = {
            "currentHour": str(current_hour),
            "studentDetails": attendance_data
        }

        # POST the attendance data to the API
        response = requests.post(api_endpoint, json=payload, headers=headers)

        if response.status_code == 200:
            return JsonResponse({"message": "Attendance data sent successfully.", "response": response.json()}, status=200)
        else:
            return JsonResponse({"error": "Failed to send attendance data.", "details": response.text}, status=response.status_code)

    except Exception as e:
        return JsonResponse({"error": "An error occurred while processing the request.", "details": str(e)}, status=500)

    # If invoked programmatically, return the status instead of JsonResponse
    return {"message": "Attendance data sent successfully."}

@csrf_exempt
def trigger_attendance_requests(request):
    if request.method == 'POST':
        try:
            current_date = datetime.date.today()

            # Fetch unique end times for the current date
            end_times = (
                Attendance.objects.filter(date=current_date)
                .values_list('to_time', flat=True)
                .distinct()
            )

            if not end_times:
                return JsonResponse({"message": "No attendance records found for today."}, status=200)

            # Trigger `send_attendance_data` for each end_time
            for end_time in end_times:
                end_time_dt = datetime.datetime.combine(current_date, end_time)
                if end_time_dt > datetime.datetime.now():
                    # Call `send_attendance_data` with the appropriate hour
                    send_attendance_data(current_hour=end_time.hour)

            return JsonResponse({"message": "Attendance data triggered for all end times."}, status=200)

        except Exception as e:
            return JsonResponse({"error": "An error occurred while processing the request.", "details": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method. Use POST."}, status=405)

