import os
import cv2
import time
import redis
import numpy as np
import pandas as pd
from datetime import datetime, date, timedelta
from insightface.app import FaceAnalysis
from sklearn.metrics import pairwise
from celery import shared_task
from django.apps import apps
import pytz
import requests



# Define IST timezone
ist_timezone = pytz.timezone('Asia/Kolkata')
# current_date = datetime.now(ist_timezone).date()
# current_time = datetime.now(ist_timezone)


CELERY_IMPORTS = ('myapp.tasks',)

@shared_task(name='myapp.tasks.capture_images_from_cameras')
def capture_images_from_cameras(rtsp_urls, start_time_str, end_time_str, output_dir, capture_interval=5):
    """
    Captures images from multiple RTSP cameras between a specific start and end time.
    """
    # Convert string times back to datetime objects and make them timezone-aware
    # start_time = datetime.fromisoformat(start_time_str).replace(tzinfo=ist_timezone)
    # end_time = datetime.fromisoformat(end_time_str).replace(tzinfo=ist_timezone)

    # start_time = datetime.combine(current_date, start_time_str)
    # end_time = datetime.combine(current_date, end_time_str)

    # This produces a naive datetime (no timezone)
    current_date = datetime.now(ist_timezone).date()

    naive_start_time = datetime.combine(current_date, start_time_str)
    naive_end_time = datetime.combine(current_date, end_time_str)
    
    # Convert from naive to IST-aware datetime
    start_time = ist_timezone.localize(naive_start_time)
    end_time = ist_timezone.localize(naive_end_time)

    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)  # This avoids the FileExistsError
    print(f"Using directory: {output_dir}")

    # Calculate the pending time until the start time
    current_time = datetime.now(ist_timezone)
    time_to_start = (start_time - current_time).total_seconds()

    if time_to_start > 0:
        print(f"Waiting for {time_to_start} seconds until the start time: {start_time}")
        time.sleep(time_to_start)

    print(f"Start time reached: {start_time}. Starting continuous capture.")

    while start_time <= datetime.now(ist_timezone) <= end_time: 
        for rtsp_url in rtsp_urls:
            cap = cv2.VideoCapture(rtsp_url)

            if not cap.isOpened():
                print(f"Error: Unable to connect to camera {rtsp_url}.")
                continue

            ret, frame = cap.read()
            if ret:
                timestamp = datetime.now(ist_timezone).strftime("%Y%m%d_%H%M%S")
                camera_id = rtsp_url.split('@')[-1].split('/')[0]  # Extract unique part of the URL for the filename
                filename = os.path.join(output_dir, f"capture_{camera_id}_{timestamp}.jpg")
                cv2.imwrite(filename, frame)
                print(f"Image captured and saved as {filename}")
            else:
                print(f"Error: Failed to capture image from {rtsp_url}.")
            
            cap.release() 

        time.sleep(capture_interval)  # Wait for the specified interval before the next round of captures

    print(f"End time reached: {end_time}. Stopping capture.")


def ml_search_algorithm(dataframe, feature_column, test_vector, name_email=['Name', 'email'], thresh=0.5):
    """Performs cosine similarity search to match embeddings."""
    dataframe = dataframe.copy()
    X_list = dataframe[feature_column].tolist()
    x = np.asarray(X_list)
    similar = pairwise.cosine_similarity(x, test_vector.reshape(1, -1))
    dataframe['cosine'] = similar.flatten()
    data_filter = dataframe.query(f'cosine >= {thresh}')
    
    if len(data_filter) > 0:
        data_filter.reset_index(drop=True, inplace=True)
        argmax = data_filter['cosine'].argmax()
        return data_filter.loc[argmax]['Name'], data_filter.loc[argmax]['email']
    return 'Unknown', 'Unknown'


# @shared_task
# def attendance_task(input_folder, output_folder):
#     """Processes attendance by detecting faces and updating the database."""
#     # Dynamically load models
#     Student = apps.get_model('myapp', 'Student')
#     Subject = apps.get_model('myapp', 'Subject')
#     Attendance = apps.get_model('myapp', 'Attendance')

#     # Configure InsightFace
#     faceapp = FaceAnalysis(name='buffalo_l', root='insightface_model', provider=['CUDAExecutionProvider'])
#     faceapp.prepare(ctx_id=0, det_size=(640, 640), det_thresh=0.5)

#     # Connect to Redis
#     redis_client = redis.StrictRedis(host='localhost', port=6379)
#     redis_client.ping()

#     # Retrieve embeddings from Redis
#     name = 'Lead:Batch_1_2023_cleaned'
#     retrive_dict = redis_client.hgetall(name)
#     retrive_series = pd.Series(retrive_dict).apply(lambda x: np.frombuffer(x, dtype=np.float32))
#     retrive_series.index = [key.decode() for key in retrive_series.index]
#     retrive_df = retrive_series.to_frame().reset_index()
#     retrive_df.columns = ['name_email', 'facial_features']
#     retrive_df[['Name', 'email']] = retrive_df['name_email'].apply(lambda x: x.split('#')).apply(pd.Series)
#     student_emails = retrive_df['email']

#     detected_faces = []

#     # Process images
#     for filename in os.listdir(input_folder):
#         filepath = os.path.join(input_folder, filename)
#         test_image = cv2.imread(filepath)

#         if test_image is None:
#             print(f"Warning: Unable to read image {filename}.")
#             continue

#         # Detect faces and extract embeddings
#         results = faceapp.get(test_image)
#         test_copy = test_image.copy()

#         for res in results:
#             x1, y1, x2, y2 = res['bbox'].astype(int)
#             embeddings = res['embedding']
#             person_name, person_email = ml_search_algorithm(
#                 retrive_df, 'facial_features', test_vector=embeddings, name_email=['Name', 'email'], thresh=0.45
#             )

#             color = (0, 255, 0) if person_email != 'Unknown' else (0, 0, 255)
#             cv2.rectangle(test_copy, (x1, y1), (x2, y2), color)
#             cv2.putText(test_copy, person_email, (x1, y1 - 10), cv2.FONT_HERSHEY_DUPLEX, 0.7, color, 1)

#             if person_email != 'Unknown' and person_email not in detected_faces:
#                 detected_faces.append(person_email)

#         # Save processed image
#         os.makedirs(output_folder, exist_ok=True)
#         output_filepath = os.path.join(output_folder, filename)
#         cv2.imwrite(output_filepath, test_copy)
#         os.remove(filepath)

#     # Update attendance using Django ORM
#     update_attendance_in_db(detected_faces, student_emails, Attendance)

# def update_attendance_in_db(detected_faces, student_emails, Attendance):
#     """Updates attendance using Django ORM."""
#     current_date = date.today()

#     for email in student_emails:
#         is_present = email in detected_faces
#         Attendance.objects.update_or_create(
#             student_email=email,
#             date=current_date,
#             defaults={'is_present': is_present}
#         )



@shared_task
def attendance_task(input_folder, output_folder, start_time_str, end_time_str, current_hour, subject_id):
    """
    1) Wait until start_time
    2) Every 10 minutes, process images, then wait 10 minutes
    3) Stop after end_time
    """
    
    # Convert string times to timezone-aware datetimes if needed
    # For example, if start_time_str and end_time_str are already isoformat with offset
    # you could do:
    # start_time = datetime.fromisoformat(start_time_str)
    # end_time   = datetime.fromisoformat(end_time_str)
    #
    # Or if they're naive or local, you might do something like:
    # ist_timezone = pytz.timezone('Asia/Kolkata')
    # naive_start = datetime.fromisoformat(start_time_str)
    # start_time  = ist_timezone.localize(naive_start)
    # ... similarly for end_time ...
    
    # This produces a naive datetime (no timezone)
    current_date = datetime.now(ist_timezone).date()

    naive_start_time = datetime.combine(current_date, start_time_str)
    naive_end_time = datetime.combine(current_date, end_time_str)
    
    # Convert from naive to IST-aware datetime
    start_time = ist_timezone.localize(naive_start_time)
    end_time = ist_timezone.localize(naive_end_time)
    
    # 1) Sleep until start_time
    current_time = datetime.now(ist_timezone)

    time_to_wait = (start_time - current_time).total_seconds()
    if time_to_wait > 0:
        time.sleep(time_to_wait)

    # 2) Initialize your faceapp, Redis, DB models, etc. outside the loop
    Student = apps.get_model('myapp', 'Student')
    Subject = apps.get_model('myapp', 'Subject')
    Attendance = apps.get_model('myapp', 'Attendance')

    faceapp = FaceAnalysis(name='buffalo_l', root='insightface_model', provider=['CUDAExecutionProvider'])
    faceapp.prepare(ctx_id=0, det_size=(640, 640), det_thresh=0.5)

    redis_client = redis.StrictRedis(host='localhost', port=6379)
    redis_client.ping()

    # Load embeddings from Redis once
    name = 'Lead:Batch_1_2023_cleaned'
    retrive_dict = redis_client.hgetall(name)
    retrive_series = pd.Series(retrive_dict).apply(lambda x: np.frombuffer(x, dtype=np.float32))
    retrive_series.index = [key.decode() for key in retrive_series.index]
    retrive_df = retrive_series.to_frame().reset_index()
    retrive_df.columns = ['name_email', 'facial_features']
    retrive_df[['Name', 'email']] = retrive_df['name_email'].apply(lambda x: x.split('#')).apply(pd.Series)
    student_emails = retrive_df['email']

    while True:
        current_time = datetime.now(ist_timezone)

        if current_time >= end_time:
            print(f"End time {end_time} reached or passed. Stopping attendance task.")
            break

        print(f"Processing images in folder: {input_folder} @ [{current_time}]")

        # Process all images in the input_folder
        detected_faces = []
        for filename in os.listdir(input_folder):
            filepath = os.path.join(input_folder, filename)
            test_image = cv2.imread(filepath)

            if test_image is None:
                print(f"Warning: Unable to read image {filename}. Skipping.")
                continue

            results = faceapp.get(test_image)
            test_copy = test_image.copy()

            for res in results:
                x1, y1, x2, y2 = res['bbox'].astype(int)
                embeddings = res['embedding']
                
                person_name, person_email = ml_search_algorithm(
                    retrive_df,
                    'facial_features',
                    test_vector=embeddings,
                    name_email=['Name', 'email'],
                    thresh=0.45
                )

                color = (0, 255, 0) if person_email != 'Unknown' else (0, 0, 255)
                cv2.rectangle(test_copy, (x1, y1), (x2, y2), color)
                cv2.putText(test_copy, person_email, (x1, y1 - 10), cv2.FONT_HERSHEY_DUPLEX, 0.7, color, 1)

                if person_email != 'Unknown' and person_email not in detected_faces:
                    detected_faces.append(person_email)

            # Save processed image
            os.makedirs(output_folder, exist_ok=True)
            output_filepath = os.path.join(output_folder, filename)
            cv2.imwrite(output_filepath, test_copy)
            os.remove(filepath)

        # 2B) Update attendance
        update_attendance_in_db(detected_faces, student_emails, current_hour, subject_id, Attendance)

        # 2C) Sleep for 10 minutes
        print(f"[{datetime.now()}] Sleeping for 10 minutes before next run.")
        time.sleep(1 * 60)  # 1 minutes in seconds

    print("Attendance task completed.")

# Keep the same helper function
def update_attendance_in_db(detected_faces, student_emails, current_hour, subject_id, Attendance):
    current_date = date.today()
    for email in student_emails:
        is_present = email in detected_faces
        Attendance.objects.update_or_create(
            student_email=email,
            date=current_date,
            hour=current_hour,
            defaults={'is_present': is_present},
            subject_id_id=subject_id
        )


@shared_task
def send_attendance_data_task(current_hour, start_time_str, end_time_str, interval_minutes=10):
    """
    Periodically sends attendance data to the Linways server every 'interval_minutes'
    from start_time to end_time + 10 minutes.
    """

    current_date = datetime.now(ist_timezone).date()

    # This produces a naive datetime (no timezone)

    naive_start_time = datetime.combine(current_date, start_time_str)
    naive_end_time = datetime.combine(current_date, end_time_str)
    
    # Convert from naive to IST-aware datetime
    start_time = ist_timezone.localize(naive_start_time)
    end_time = ist_timezone.localize(naive_end_time)

    # Ensure we handle them as aware datetime objects
    # (If they are naive, localize them: ist_timezone.localize(...))
    # Add 10 minutes to end_time
    end_time_extended = end_time + timedelta(minutes=interval_minutes)

    # Sleep until we reach start_time (if current time is before start_time)
    current_time = datetime.now(ist_timezone)
    wait_seconds = (start_time - current_time).total_seconds()
    if wait_seconds > 0:
        time.sleep(wait_seconds)

    # Now run a loop until end_time_extended
    while True:
        current_time = datetime.now(ist_timezone)
        if current_time > end_time_extended:
            print(f"[{current_time}] Past end_time; stopping attendance data submission.")
            break

        # Send attendance data
        response_info = send_attendance_data(current_hour)
        print(f"[{current_time}] Sent attendance data. Response: {response_info}")

        # Sleep for interval_minutes
        time.sleep(interval_minutes * 60)

def send_attendance_data(current_hour):
    # Dynamically load models so tasks can run without import issues
    Attendance = apps.get_model('myapp', 'Attendance')

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
            return {"error": "Failed to send attendance data.", "status_code": response.status_code, "details": response.text}

    except Exception as e:
        return {"error": "An error occurred while processing the request.", "details": str(e)}