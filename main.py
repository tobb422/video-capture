import cv2
import datetime
import sys
import termios
from timeout_decorator import timeout, TimeoutError
import pyaudio
from pydub import AudioSegment
import wave
import ffmpeg
import os
import requests
import json
import threading
import copy
from evdev import InputDevice

TOKEN = ''
CHANNEL = '#video-capture'
WEBHOOK_URL = ''

fd = sys.stdin.fileno()
new = termios.tcgetattr(fd)
new[3] &= ~termios.ICANON
new[3] &= ~termios.ECHO
termios.tcsetattr(fd, termios.TCSANOW, new)

@timeout(0.01)
def waitClick(device):
    try:
        return device.read_one()
    except Exception:
        return ''

camera = cv2.VideoCapture(0)
fps = 8.61328125
w = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
fourcc = cv2.VideoWriter_fourcc(*'XVID')

P = pyaudio.PyAudio()
CHUNK = 1024*5
CHANNELS = 1
FORMAT = pyaudio.paInt16
RATE = 44100
stream = P.open(format=FORMAT, channels=CHANNELS, rate=RATE, frames_per_buffer=CHUNK, input=True, output=True)


def worker(frames, voices):
    now = datetime.datetime.today().strftime("%Y%m%d-%H%M%S")
    video = cv2.VideoWriter(now+'-tmp.avi', fourcc, fps, (w, h))
    for f in frames:
        video.write(f)

    wf = wave.open(now+'-tmp.wav', 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(P.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(voices))
    wf.close()

    base_sound = AudioSegment.from_file(now+'-tmp.wav', format='wav')
    base_sound.export(now+'-tmp.mp3', format="mp3")

    audio_stream = ffmpeg.input(now+'-tmp.mp3')
    video_stream = ffmpeg.input(now+'-tmp.avi')
    title = now+'.mov'
    r_stream = ffmpeg.output(video_stream, audio_stream, now+'-tmp.mp4', vcodec="copy", acodec="aac")
    ffmpeg.run(r_stream)

    ffmpeg.run(ffmpeg.output(ffmpeg.input(now+'-tmp.mp4'), title, pix_fmt='yuv420p'))

    os.remove(now+'-tmp.avi')
    os.remove(now+'-tmp.wav')
    os.remove(now+'-tmp.mp3')
    os.remove(now+'-tmp.mp4')

    data = {
        'token': TOKEN,
        'channels': CHANNEL,
        'initial_comment': 'ええ感じの動画撮れたわ。'
    }

    files = {'file': open(title, 'rb')}
    r = requests.post('https://slack.com/api/files.upload', params=data, files=files)
    res = json.loads(r.text)
    if res['ok']:
        os.remove(title)


frames = []
voices = []
while True:
    ret, frame = camera.read()
    frames.append(frame)
    if len(frames) > fps*31:
        frames.pop(0)

    input = stream.read(CHUNK, exception_on_overflow=False)
    voices.append(input)
    if len(voices) > fps*31:
        voices.pop(0)

    device = InputDevice('/dev/input/event1')
    event = device.read_one()
    if event != None:
        res = requests.post(WEBHOOK_URL, data=json.dumps({
            'text': 'いまから動画加工していくで〜'
        }))
        fs = copy.copy(frames)
        vs = copy.copy(voices)
        t = threading.Thread(target=worker, args=(fs, vs))
        t.start()
