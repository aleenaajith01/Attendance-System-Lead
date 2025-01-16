import schedule
import time
import requests

url1 = "http://127.0.0.1:8000/backend/fetch-update-data/"
url2 = "http://127.0.0.1:8000/backend/trigger-attendance-requests/"
url3 = "http://127.0.0.1:8000/backend/fetch-and-capture-images/"
url4 = "http://127.0.0.1:8000/backend/take_attendance/"


def send_request(url):
    try:
        print(f"Sending request to the endpoint {url}...")
        response = requests.get(url)
        
        if response.status_code == 200:
            print("Request successful:", response.json())
        else:
            print("Request failed with status code:", response.status_code)
            print("Response:", response.text)
    except Exception as e:
        print("Error occurred while sending the request:", str(e))

if __name__ == "__main__":
    # Schedule the tasks
    schedule.every().day.at("14:40").do(lambda: send_request(url1))  # Replace time as needed
    # schedule.every().day.at("07:05").do(lambda: send_request(url2))  # Replace time as needed
    schedule.every().day.at("14:40").do(lambda: send_request(url3))
    # schedule.every().day.at("11:42").do(lambda: send_request(url4))

    print("Scheduler is running...")

    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(6)  # Wait for the next minute
