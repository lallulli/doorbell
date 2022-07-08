from threading import Thread
from time import sleep
import requests
import logging

"""
Periodically contact a URL, to make sure that the service is alive 
"""

class Watchdog(Thread):
    def __init__(self, url, json_data=None, period_seconds=5 * 60):
        super().__init__()
        self.period = period_seconds
        self.url = url
        self.json_data = json_data

    def run(self):
        while True:
            try:
                r = requests.post(self.url, json=self.json_data)
                # print(r.status_code)
                # print(r.text)
            except Exception as e:
                logging.error(str(e))
            sleep(self.period)

