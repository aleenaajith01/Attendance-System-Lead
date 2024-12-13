from django.http import JsonResponse
from .models import Student, Subject, Attendance
import requests
from datetime import datetime, date # Correct import for datetime
from django.views.decorators.csrf import csrf_exempt
import json
import cv2
import os  # Import the os module
import time

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
            current_date = datetime.date.today()  # Use datetime.date for the current date
            
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



def capture_images_from_cameras(rtsp_urls, start_time, end_time, capture_interval=5):
    """
    Captures images from multiple RTSP cameras between a specific start and end time.

    Args:
        rtsp_urls (list): List of RTSP URLs of the cameras.
        start_time (datetime): The start time to begin capturing.
        end_time (datetime): The end time to stop capturing.
        capture_interval (int): Time interval between captures in seconds (default is 5 seconds).
    """
    # Ensure the `media/captures` folder exists
    output_dir = "media/captures"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)  # Create the directory if it doesn't exist
        print(f"Created directory: {output_dir}")

    print(f"Waiting for the start time: {start_time}")
    while datetime.now() < start_time:
        time.sleep(1)  # Sleep for 1 second
    print(f"Start time reached: {start_time}. Starting continuous capture.")

    while datetime.now() <= end_time:
        for rtsp_url in rtsp_urls:
            print(f"Connecting to camera: {rtsp_url}")
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
    Fetches distinct start and end times from the Attendance table
    and captures images from RTSP cameras based on those times.
    """
    try:
        # Fetch distinct start and end times for the current day
        current_date = datetime.now().date()
        attendance_records = Attendance.objects.filter(date=current_date).distinct()

        start_times = attendance_records.values_list('from_time', flat=True).distinct()
        end_times = attendance_records.values_list('to_time', flat=True).distinct()

        if not start_times or not end_times:
            return JsonResponse({"message": "No start or end times found for today."}, status=200)

        # Convert time fields into datetime objects
        start_end_times = [
            (datetime.combine(current_date, start_time), datetime.combine(current_date, end_time))
            for start_time, end_time in zip(start_times, end_times)
        ]

        # List of RTSP URLs (can be fetched dynamically or stored in a settings/config file)
        rtsp_urls = [
            'rtsp://admin:password123@192.168.0.240/cam/realmonitor?channel=1&subtype=0',
            'rtsp://admin:password123@192.168.0.241/cam/realmonitor?channel=1&subtype=0',
            'rtsp://admin:password123@192.168.0.242/cam/realmonitor?channel=1&subtype=0',
            'rtsp://admin:password123@192.168.0.243/cam/realmonitor?channel=1&subtype=0',
        ]

        # Start capturing images for each start and end time
        for start_time, end_time in start_end_times:
            print(f"Capturing images from {start_time} to {end_time}.")
            capture_images_from_cameras(rtsp_urls, start_time, end_time)

        return JsonResponse({"message": "Images captured successfully for all time slots."}, status=200)

    except Exception as e:
        return JsonResponse({"error": "An error occurred while processing the request.", "details": str(e)}, status=500)
