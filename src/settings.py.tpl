import sounddevice as sd

# Uncomment next line to set the id of the device to use for sound capturing.
# Available devices can be obtained using the following command:
# `python -m sounddevice`

# sd.default.device = 1

DEBUG = True
FREQUENCY = 44100
DURATION = 0.16
MIN_ENERGY_RATIO = 100
SIMILARITY_THRESHOLD = 0.7
MIN_CONSECUTIVE_OK = 3
TRIGGER_MIN_INTERVAL = timedelta(seconds=10)


# Set a webhook URL to call a webhook on sound detection

WEBHOOK_URL = None
# WEBHOOK_URL = 'https://maker.ifttt.com/trigger/MY_EVENT/with/key/MY_KEY={sound}'
