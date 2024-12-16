from django.http import JsonResponse
from .models import Student, Subject, Attendance
import requests
from datetime import datetime, date # Correct import for datetime
from django.views.decorators.csrf import csrf_exempt
import json
import cv2
import os  # Import the os module
import time
import threading


@csrf_exempt
def fetch_and_update_data(request):
    # Fetch data from Linways API
    api_key = 'CQTnCjhviK'
    api_secret_key = 'LEJ8TzUjzdR6iGU2G'
    api_endpoint = 'https://uatleadv4.linways.com/lin-api/v1/academics/student/get-student-data-for-attendance/'
    today_date = datetime.today().date().strftime('%Y-%m-%d')  # Corrected usage

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
            return {"message": "Attendance data sent successfully.", "response": response.json()}
        else:
            return {"error": "Failed to send attendance data.", "details": response.text}

    except Exception as e:
        return {"error": "An error occurred while processing the request.", "details": str(e)}

@csrf_exempt
def trigger_attendance_requests(request):
    if request.method == 'GET':
        try:
            current_date = date.today()  # Use datetime.date for the current date
            
            # Fetch unique end times for the current date
            end_times = (
                Attendance.objects.filter(date=current_date)
                .values_list('to_time', flat=True)
                .distinct()
            )

            if not end_times:
                return JsonResponse({"message": "No attendance records found for today."}, status=200)

            # Trigger `send_attendance_data_helper` for each end_time
            for end_time in end_times:
                end_time_dt = datetime.combine(current_date, end_time)
                if end_time_dt > datetime.now():
                    # Call `send_attendance_data_helper` with the appropriate hour
                    result = send_attendance_data(current_hour=end_time.hour)
                    if "error" in result:
                        return JsonResponse(result, status=500)

            return JsonResponse({"message": "Attendance data triggered for all end times."}, status=200)

        except Exception as e:
            return JsonResponse({"error": "An error occurred while processing the request.", "details": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method. Use POST."}, status=405)



def capture_images_from_cameras(rtsp_urls, start_time, end_time, output_dir, capture_interval=5):
    """
    Captures images from multiple RTSP cameras between a specific start and end time.
    """
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)  # This avoids the FileExistsError
    print(f"Using directory: {output_dir}")

    print(f"Waiting for the start time: {start_time}")
    while datetime.now() < start_time:
        time.sleep(1)  # Sleep for 1 second
    print(f"Start time reached: {start_time}. Starting continuous capture.")

    while start_time <= datetime.now() <= end_time:
        for rtsp_url in rtsp_urls:
            # print(f"Connecting to camera: {rtsp_url}")
            cap = cv2.VideoCapture(rtsp_url)

            if not cap.isOpened():
                print(f"Error: Unable to connect to camera {rtsp_url}.")
                continue

            ret, frame = cap.read()
            if ret:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                camera_id = rtsp_url.split('@')[-1].split('/')[0]  # Extract unique part of the URL for the filename
                filename = os.path.join(output_dir, f"capture_{camera_id}_{timestamp}.jpg")
                cv2.imwrite(filename, frame)
                print(f"Image captured and saved as {filename}")
            else:
                print(f"Error: Failed to capture image from {rtsp_url}.")
            
            cap.release()

        time.sleep(capture_interval)  # Wait for the specified interval before the next round of captures

    print(f"End time reached: {end_time}. Stopping capture.")



@csrf_exempt
def fetch_and_capture_images(request):
    """
    Fetches start and end times from the database and captures images from multiple RTSP cameras using multithreading.
    """
    try:
        # Fetch distinct start times along with their corresponding end times and hours for the current day
        current_date = datetime.now().date()
        attendance_records = Attendance.objects.filter(date=current_date).values('from_time', 'to_time', 'hour').distinct()

        if not attendance_records:
            return JsonResponse({"message": "No start or end times found for today."}, status=200)

        # Convert time fields into datetime objects
        start_end_times_hour = [
            (
                datetime.combine(current_date, record['from_time']),
                datetime.combine(current_date, record['to_time']),
                record['hour']
            )
            for record in attendance_records
        ]
        print(start_end_times_hour)

        # List of RTSP URLs for all classrooms
        classrooms = {
            "Class_A": [
                'rtsp://admin:password123@192.168.0.220/cam/realmonitor?channel=1&subtype=0',
                'rtsp://admin:password123@192.168.0.221/cam/realmonitor?channel=1&subtype=0',
                'rtsp://admin:password123@192.168.0.222/cam/realmonitor?channel=1&subtype=0',
                'rtsp://admin:password123@192.168.0.223/cam/realmonitor?channel=1&subtype=0'
            ],
            "Class_B": [
                'rtsp://admin:password123@192.168.0.224/cam/realmonitor?channel=1&subtype=0',
                'rtsp://admin:password123@192.168.0.225/cam/realmonitor?channel=1&subtype=0',
                'rtsp://admin:password123@192.168.0.226/cam/realmonitor?channel=1&subtype=0',
                'rtsp://admin:password123@192.168.0.227/cam/realmonitor?channel=1&subtype=0'
            ],
            "Class_C" : [
                'rtsp://admin:password123@192.168.0.228/cam/realmonitor?channel=1&subtype=0',
                'rtsp://admin:password123@192.168.0.229/cam/realmonitor?channel=1&subtype=0',
                'rtsp://admin:password123@192.168.0.230/cam/realmonitor?channel=1&subtype=0',
                'rtsp://admin:password123@192.168.0.231/cam/realmonitor?channel=1&subtype=0'
            ],  
            "Class_D" : [
                'rtsp://admin:password123@192.168.0.232/cam/realmonitor?channel=1&subtype=0',
                'rtsp://admin:password123@192.168.0.233/cam/realmonitor?channel=1&subtype=0',
                'rtsp://admin:password123@192.168.0.234/cam/realmonitor?channel=1&subtype=0',
                'rtsp://admin:password123@192.168.0.235/cam/realmonitor?channel=1&subtype=0'
            ],          
            "Class_E" : [
                'rtsp://admin:password123@192.168.0.236/cam/realmonitor?channel=1&subtype=0',
                'rtsp://admin:password123@192.168.0.237/cam/realmonitor?channel=1&subtype=0',
                'rtsp://admin:password123@192.168.0.238/cam/realmonitor?channel=1&subtype=0',
                'rtsp://admin:password123@192.168.0.239/cam/realmonitor?channel=1&subtype=0'
            ],   
            "Class_F" : [
                'rtsp://admin:password123@192.168.0.240/cam/realmonitor?channel=1&subtype=0',
                'rtsp://admin:password123@192.168.0.241/cam/realmonitor?channel=1&subtype=0',
                'rtsp://admin:password123@192.168.0.242/cam/realmonitor?channel=1&subtype=0',
                'rtsp://admin:password123@192.168.0.243/cam/realmonitor?channel=1&subtype=0'
                        
            ]}
            # Add other classes here

        threads = []

        # Start capturing images for each classroom and time slot using threads
        for class_name, rtsp_urls in classrooms.items():
            for start_time, end_time, current_hour in start_end_times_hour:
                output_dir = f"media/captures/{current_date}/Hour_{current_hour}/{class_name}"
                thread = threading.Thread(
                    target=capture_images_from_cameras,
                    args=(rtsp_urls, start_time, end_time, output_dir)
                )
                threads.append(thread)
                thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        return JsonResponse({"message": "Images captured successfully for all classrooms."}, status=200)

    except Exception as e:
        return JsonResponse({"error": "An error occurred while processing the request.", "details": str(e)}, status=500)
