from datetime import datetime, timedelta
import sounddevice as sd
import numpy as np
import requests
import logging
import math
import sys
import os

DEBUG = True
FREQUENCY = 44100
DURATION = 0.10
MIN_ENERGY_RATIO = 100
SIMILARITY_THRESHOLD = 0.8
MIN_CONSECUTIVE_OK = 3
TRIGGER_MIN_INTERVAL = timedelta(seconds=10)

logging.getLogger().setLevel(logging.DEBUG if DEBUG else logging.WARNING)
stop = False


def generate_clip_fft(duration=3, normalize=True):
    global stop
    stop = False
    s = sd.Stream(FREQUENCY, channels=1)
    s.start()
    while not stop:
        myrec = s.read(int(duration * FREQUENCY))[0]
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
        if p > SIMILARITY_THRESHOLD:
            self.n_ok += 1
            if self.n_ok >= MIN_CONSECUTIVE_OK:
                logging.info("+ {} {} {}".format(self.filename, self.n_ok, p))
                if not self.triggered and self.callback is not None and (self.next_trigger is None or datetime.now() >= self.next_trigger):
                    self.triggered = True
                    logging.info("Callback {}".format(self.filename))
                    self.callback(self)
        else:
            if self.n_ok > MIN_CONSECUTIVE_OK:
                logging.info("- {}\n".format(self.filename))
            self.n_ok = 0
            if self.triggered:
                self.triggered = False
                self.next_trigger = datetime.now() + TRIGGER_MIN_INTERVAL
                logging.info("Next trigger at {}".format(self.next_trigger))


def record_sample():
    global stop
    capturing = False
    fft_length = int((DURATION * FREQUENCY) / 2) + 1
    F = np.zeros((fft_length,), dtype=np.float64)
    fold = None
    for i, f in enumerate(generate_clip_fft(DURATION, False)):
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
        if not capturing and np.dot(f, f) > energy * MIN_ENERGY_RATIO:
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


def sample_callback(sd):
    print("Called callback ", sd.filename)


def load_and_start_detecting():
    """
    Load sounds in current directory and start liste
    """
    filenames = os.listdir()
    detectors = []
    for f in filenames:
        if f.endswith('.npy'):
            detectors.append(SoundDetector(f, sample_callback))
    for G in generate_clip_fft(DURATION):
        for sd in detectors:
            sd.compare(G)


if __name__ == '__main__':
    if len(sys.argv) == 2:
        name = sys.argv[-1]
        print("Recording ", name)
        record_and_save_sample(name)
    else:
        print("Listening for sounds")
        load_and_start_detecting()

