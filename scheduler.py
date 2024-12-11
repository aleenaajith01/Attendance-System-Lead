# import schedule
# import time
# import requests

# def send_request():
#     try:
#         # URL of your Django endpoint
#         url = "http://127.0.0.1:8000/fetch-update-data/"
        
#         print("Sending request to the endpoint...")
#         response = requests.get(url)
        
#         if response.status_code == 200:
#             print("Request successful:", response.json())
#         else:
#             print("Request failed with status code:", response.status_code)
#             print("Response:", response.text)
#     except Exception as e:
#         print("Error occurred while sending the request:", str(e))



# if __name__ == "__main__":

#     # Schedule the task at 7:00 AM
#     schedule.every().day.at("22:39").do(send_request)

#     print("Scheduler is running...")

#     # Keep the script running
#     while True:
#         schedule.run_pending()
#         time.sleep(60)  # Wait for the next minute

import schedule
import time
import requests

def fetch_and_update_data():
    try:
        # URL of your Django endpoint for fetching and updating data
        url = "http://127.0.0.1:8000/fetch-update-data/"
        
        print("Sending fetch-update request to the endpoint...")
        response = requests.get(url)
        
        if response.status_code == 200:
            print("Fetch-update request successful:", response.json())
        else:
            print("Fetch-update request failed with status code:", response.status_code)
            print("Response:", response.text)
    except Exception as e:
        print("Error occurred while sending the fetch-update request:", str(e))


def send_attendance_request():
    try:
        # URL of your Django endpoint for sending attendance data
        url = "http://127.0.0.1:8000/trigger-attendance-requests/"
        
        print("Sending attendance request to the endpoint...")
        response = requests.post(url)
        
        if response.status_code == 200:
            print("Attendance request successful:", response.json())
        else:
            print("Attendance request failed with status code:", response.status_code)
            print("Response:", response.text)
    except Exception as e:
        print("Error occurred while sending the attendance request:", str(e))


if __name__ == "__main__":

    # Schedule the tasks
    schedule.every().day.at("20:34").do(fetch_and_update_data)  # Replace time as needed
    schedule.every().day.at("20:35").do(send_attendance_request)  # Replace time as needed

    print("Scheduler is running...")

    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Wait for the next minute
