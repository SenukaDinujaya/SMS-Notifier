import requests
from app.config import Config
class LogSender:

    def __init__(self) -> None:
        self.log_endpoint = 'http://localhost:5000/log'


    def send_log(self, data:list):
        try:
            response = requests.post(self.log_endpoint, json={'data': data+[Config.LOG_TOKEN]})
            if response.status_code == 200:
                pass
            else:
                print(f"Failed to send log. Status code: {response.status_code}")
        except Exception as e:
            print(f"An error occurred while sending log: {e}")