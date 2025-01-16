from django.http import JsonResponse
from .models import Student, Subject, Attendance
import requests
from datetime import datetime, date, timedelta # Correct import for datetime
from django.views.decorators.csrf import csrf_exempt
import json
import cv2
import os  # Import the os module
import time
import threading
import aiohttp
import asyncio
from django.utils.decorators import async_only_middleware
from asgiref.sync import sync_to_async
from .tasks import capture_images_from_cameras, attendance_task, send_attendance_data_task, process_attendance_last
import pytz

# Define IST timezone
ist_timezone = pytz.timezone('Asia/Kolkata')



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
                if end_time_dt > datetime.now(ist_timezone):
                    # Call `send_attendance_data_helper` with the appropriate hour
                    result = send_attendance_data(current_hour=end_time.hour)
                    if "error" in result:
                        return JsonResponse(result, status=500)

            return JsonResponse({"message": "Attendance data triggered for all end times."}, status=200)

        except Exception as e:
            return JsonResponse({"error": "An error occurred while processing the request.", "details": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method. Use POST."}, status=405)



async def capture_images_from_classroom(rtsp_urls, output_dir, start_time, end_time, capture_interval=5):
    """
    Asynchronously captures images from RTSP cameras for a specific classroom.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    while datetime.now(ist_timezone) < start_time:
        await asyncio.sleep(1)

    while datetime.now(ist_timezone) <= end_time:
        tasks = []
        for rtsp_url in rtsp_urls:
            tasks.append(capture_single_image(rtsp_url, output_dir))
        await asyncio.gather(*tasks)
        await asyncio.sleep(capture_interval)

async def capture_single_image(rtsp_url, output_dir):
    """
    Captures a single image from an RTSP stream asynchronously.
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(rtsp_url) as response:
            if response.status == 200:
                timestamp = datetime.now(ist_timezone).strftime("%Y%m%d_%H%M%S")
                camera_id = rtsp_url.split('@')[-1].split('/')[0]
                filename = os.path.join(output_dir, f"capture_{camera_id}_{timestamp}.jpg")
                with open(filename, 'wb') as f:
                    f.write(await response.read())
            else:
                print(f"Failed to capture from {rtsp_url}")




        

@csrf_exempt
def fetch_and_capture_images(request):
    """
    Fetches start and end times and triggers Celery tasks to capture images.
    """
    try:
        current_date = datetime.now(ist_timezone).date()
        
        attendance_records = Attendance.objects.filter(date=current_date).values('from_time', 'to_time', 'hour', 'subject_id_id').distinct()

        if not attendance_records:
            return JsonResponse({"message": "No schedules for today."}, status=200)
        
        # Convert time fields into datetime objects
        # start_end_times_hour = [
        #     (
        #         datetime.combine(current_date, record['from_time']),
        #         datetime.combine(current_date, record['to_time']),
        #         record['hour']
        #     )
        #     for record in attendance_records
        # ]

        start_end_times_hour = [
            (
                record['from_time'],
                record['to_time'],
                record['hour'],
                record['subject_id_id']
            )
            for record in attendance_records
        ]

        print(start_end_times_hour)

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
            ]
            # "Class_D" : [
            #     'rtsp://admin:password123@192.168.0.232/cam/realmonitor?channel=1&subtype=0',
            #     'rtsp://admin:password123@192.168.0.233/cam/realmonitor?channel=1&subtype=0',
            #     'rtsp://admin:password123@192.168.0.234/cam/realmonitor?channel=1&subtype=0',
            #     'rtsp://admin:password123@192.168.0.235/cam/realmonitor?channel=1&subtype=0'
            # ],          
            # "Class_E" : [
            #     'rtsp://admin:password123@192.168.0.236/cam/realmonitor?channel=1&subtype=0',
            #     'rtsp://admin:password123@192.168.0.237/cam/realmonitor?channel=1&subtype=0',
            #     'rtsp://admin:password123@192.168.0.238/cam/realmonitor?channel=1&subtype=0',
            #     'rtsp://admin:password123@192.168.0.239/cam/realmonitor?channel=1&subtype=0'
            # ],   
            # "Class_F" : [
            #     'rtsp://admin:password123@192.168.0.240/cam/realmonitor?channel=1&subtype=0',
            #     'rtsp://admin:password123@192.168.0.241/cam/realmonitor?channel=1&subtype=0',
            #     'rtsp://admin:password123@192.168.0.242/cam/realmonitor?channel=1&subtype=0',
            #     'rtsp://admin:password123@192.168.0.243/cam/realmonitor?channel=1&subtype=0'
                        
            # ]
            }

        # Schedule tasks for each classroom
        for class_name, rtsp_urls in classrooms.items():
            for start_time, end_time, current_hour, subject_id in start_end_times_hour:

                # initialize input and output folders
                capture_dir = f"media/captured_images/{current_date}/Hour_{current_hour}/{class_name}"
                processed_dir = f"media/processed_images/{current_date}/Hour_{current_hour}/{class_name}"
                
                # end_time is a TimeField, so we need to combine with current_date
                naive_start_dt = datetime.combine(current_date, start_time)
                start_dt = ist_timezone.localize(naive_start_dt)  # make it aware

                # # Capture images from classrooms
                # capture_images_from_cameras.delay(    # run the task from the called time till endtime
                #     rtsp_urls = rtsp_urls,
                #     start_time_str = start_time,
                #     end_time_str = end_time,
                #     output_dir = capture_dir,
                #     capture_interval = 60
                # )

                # capture classroom images  from classrooms for time table
                capture_images_from_cameras.apply_async(     # call & run the task from the start time only
                    kwargs={
                         'rtsp_urls' : rtsp_urls,
                        'start_time_str' : start_time,
                        'end_time_str' : end_time,
                        'output_dir' : capture_dir,
                        'capture_interval' : 60
                    },
                    eta=start_dt  # run at this exact datetime
                )

                # # process the captured images while capturing
                # attendance_task.delay(    # run the task from the called time till endtime
                #     input_folder = capture_dir,
                #     output_folder = processed_dir,
                #     start_time_str = start_time,
                #     end_time_str = end_time,
                #     current_hour = current_hour,
                #     subject_id = subject_id
                # )
                
                # For processing the captured Images
                attendance_task.apply_async(        # call & run the task from the start time only
                    kwargs={
                        'input_folder' : capture_dir,
                        'output_folder' : processed_dir,
                        'start_time_str' : start_time,
                        'end_time_str' : end_time,
                        'current_hour' : current_hour,
                        'subject_id' : subject_id
                    },
                    eta=start_dt  # run at this exact datetime
                )

                ## run the task from the call time itself 
                # send_attendance_data_task.delay(  # run the task from the called time till endtime
                #     current_hour = current_hour, 
                #     start_time_str = start_time, 
                #     end_time_str = end_time, 
                #     interval_minutes=10
                # )

                ## For sending the attendance data to Linways in every 10 min
                send_attendance_data_task.apply_async(      # call & run the task from the start time only
                    kwargs={
                        'current_hour' : current_hour, 
                        'start_time_str' : start_time, 
                        'end_time_str' : end_time, 
                        'interval_minutes' : 10
                    },
                    eta=start_dt  # run at this exact datetime
                )
                

        return JsonResponse({"message": "Image capture tasks scheduled successfully for all classrooms."}, status=200)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def take_attendance(request):

    current_date = datetime.now(ist_timezone).date()
    
    attendance_records = Attendance.objects.filter(date=current_date).values('from_time', 'to_time', 'hour', 'subject_id_id').distinct()

    if not attendance_records:
        return JsonResponse({"message": "No schedules for today."}, status=200)
    

    start_end_times_hour = [
        (
            record['from_time'],
            record['to_time'],
            record['hour'],
            record['subject_id_id']
        )
        for record in attendance_records
    ]
    # classrooms = ['Class_A', 'Class_B', 'Class_C', 'Class_D', 'Class_E', 'CLass_F']
    classrooms = ['Class_A', 'Class_B']

    # Schedule tasks for each classroom
    for class_name in classrooms:
        for start_time, end_time, current_hour, subject_id in start_end_times_hour:

            # initialize input and output folders
            capture_dir = f"media/captured_images/{current_date}/Hour_{current_hour}/{class_name}"
            processed_dir = f"media/processed_images/{current_date}/Hour_{current_hour}/{class_name}"
            
            # Combine date + end_time -> local (IST) aware datetime
            # end_time is a TimeField, so we need to combine with current_date
            naive_end_dt = datetime.combine(current_date, end_time)
            end_dt = ist_timezone.localize(naive_end_dt)  # make it aware

            # If end_dt is in the past, decide whether to skip or run now
            now_ist = datetime.now(ist_timezone)
            if end_dt < now_ist:
                # Either skip or schedule immediately.
                # For example, schedule now + 10 seconds:
                end_dt = now_ist + timedelta(seconds=10)

            # Schedule Celery to run at end_dt
            process_attendance_last.apply_async(
                kwargs={
                    'input_folder': capture_dir,
                    'output_folder': processed_dir,
                    'current_hour': current_hour,
                    'subject_id': subject_id
                },
                eta=end_dt  # run at this exact datetime
            )

    return JsonResponse({"message": "Scheduled processing at end_time for each classroom."}, status=200)


def data_for_frontend_dashboard(request):
    """
    For sending data from database to frontend.
    """
    # Count all Student objects in the database
    total_students = Student.objects.count()
    
    # Return a JSON response
    return JsonResponse({
        "total_students": total_students
    })