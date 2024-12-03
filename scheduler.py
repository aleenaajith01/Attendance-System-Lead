import schedule
import time
import requests

def send_request():
    try:
        # URL of your Django endpoint
        url = "http://127.0.0.1:8000/fetch-update-data/"
        
        print("Sending request to the endpoint...")
        response = requests.get(url)
        
        if response.status_code == 200:
            print("Request successful:", response.json())
        else:
            print("Request failed with status code:", response.status_code)
            print("Response:", response.text)
    except Exception as e:
        print("Error occurred while sending the request:", str(e))



if __name__ == "__main__":

    # Schedule the task at 7:00 AM
    schedule.every().day.at("22:39").do(send_request)

    print("Scheduler is running...")

    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Wait for the next minute
