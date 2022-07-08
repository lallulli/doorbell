from watchdog import Watchdog
from datetime import datetime
import sounddevice as sd
import numpy as np
import requests
import settings
import logging
import math
import sys
import os


logging.getLogger().setLevel(logging.DEBUG if settings.DEBUG else logging.WARNING)
stop = False


def generate_clip_fft(duration=3, normalize=True):
    global stop
    stop = False
    s = sd.Stream(settings.FREQUENCY, channels=1)
    s.start()
    while not stop:
        myrec = s.read(int(duration * settings.FREQUENCY))[0]
        f = np.fft.rfft(myrec[:,0])
        F = np.abs(f)
        if normalize:
            F = F / math.sqrt(np.dot(F, F))
        yield F


class SoundDetector:
    def __init__(self, filename, callback=None):
        """
        Init sound comparer

        :param filename: name of fft numpy file
        :param callback: function that will be called on sound detection.
            callback will get as parameter the instance of this class (i.e., self)
        """
        self.filename = filename
        self.F = np.load(filename)
        self.n_ok = 0
        self.triggered = False
        self.next_trigger = None
        self.callback = callback

    def compare(self, G):
        """
        Compare normalized fft's F and G
        """
        p = np.dot(self.F, G)
        if p > settings.SIMILARITY_THRESHOLD:
            self.n_ok += 1
            if self.n_ok >= settings.MIN_CONSECUTIVE_OK:
                logging.info("+ {} {} {}".format(self.filename, self.n_ok, p))
                if not self.triggered and self.callback is not None and (self.next_trigger is None or datetime.now() >= self.next_trigger):
                    self.triggered = True
                    logging.info("Callback {}".format(self.filename))
                    self.callback(self)
        else:
            if self.n_ok > settings.MIN_CONSECUTIVE_OK:
                logging.info("- {}\n".format(self.filename))
            self.n_ok = 0
            if self.triggered:
                self.triggered = False
                self.next_trigger = datetime.now() + settings.TRIGGER_MIN_INTERVAL
                logging.info("Next trigger at {}".format(self.next_trigger))


def record_sample():
    global stop
    capturing = False
    fft_length = int((settings.DURATION * settings.FREQUENCY) / 2) + 1
    F = np.zeros((fft_length,), dtype=np.float64)
    fold = None
    for i, f in enumerate(generate_clip_fft(settings.DURATION, False)):
        if i < 5:
            continue
        if i == 5:
            print("Waiting for sound")
            energy = np.dot(f, f)
            continue
        if capturing:
            if np.dot(f, f) < energy * 2:
                print("Capturing done")
                capturing = False
                stop = True
                # Discard last clip
                F -= fold
            else:
                F += f
        if not capturing and np.dot(f, f) > energy * settings.MIN_ENERGY_RATIO:
            print("Capturing")
            # Start capturing, but discard this clip
            capturing = True
        fold = f
        # print(np.dot(f, f))
    Fnorm = F / math.sqrt(np.dot(F, F))
    return Fnorm


def record_and_save_sample(filename):
    f = record_sample()
    np.save(filename, f)


def webhook_callback(sd):
    name, ext = os.path.splitext(sd.filename)
    print("Sound detected:", name)
    if settings.WEBHOOK_URL is not None:
        requests.get(settings.WEBHOOK_URL.format(sound=name))


def load_and_start_detecting():
    """
    Load sounds in current directory and start liste
    """
    filenames = os.listdir()
    detectors = []
    for f in filenames:
        if f.endswith('.npy'):
            detectors.append(SoundDetector(f, webhook_callback))
    for G in generate_clip_fft(settings.DURATION):
        for sd in detectors:
            sd.compare(G)


if __name__ == '__main__':
    if len(sys.argv) == 2:
        name = sys.argv[-1]
        print("Recording ", name)
        record_and_save_sample(name)
    else:
        print("Listening for sounds")
        if settings.WATCHDOG_URL is not None:
            w = Watchdog(settings.WATCHDOG_URL, settings.WATCHDOG_JSON_DATA)
            w.start()
        load_and_start_detecting()

