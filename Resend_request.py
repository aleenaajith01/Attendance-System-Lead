import requests
import json

def resend_attendance_data():
    # File containing the JSON data
    json_file_path = 'attendance_data.json'

    # Load the JSON data from the file
    try:
        with open(json_file_path, 'r') as file:
            attendance_data = json.load(file)
    except FileNotFoundError:
        print(f"File not found: {json_file_path}")
        return
    except json.JSONDecodeError:
        print(f"Error decoding JSON from file: {json_file_path}")
        return

    # API endpoint and headers
    api_endpoint = 'https://uatleadv4.linways.com/lin-api/v1/academics/student/mark-attendance/'
    api_key = 'CQTnCjhviK'
    api_secret_key = 'LEJ8TzUjzdR6iGU2G'

    headers = {
        'Apikey': api_key,
        'Apisecretkey': api_secret_key,
        'Content-Type': 'application/json'
    }

    # Make the POST request
    print("Sending attendance data to the API...")
    response = requests.post(api_endpoint, json={"attendanceData": attendance_data}, headers=headers)

    # Check the response status
    if response.status_code == 200:
        print("Attendance data sent successfully.")
        print(response.json())
    else:
        print(f"Failed to send attendance data. Status code: {response.status_code}")
        print(response.text)

# Call the function
resend_attendance_data()
