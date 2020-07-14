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

fd = sys.stdin.fileno()
new = termios.tcgetattr(fd)
new[3] &= ~termios.ICANON
new[3] &= ~termios.ECHO
termios.tcsetattr(fd, termios.TCSANOW, new)

@timeout(0.01)
def waitKey(key):
    try:
        return key.read(1)
    except Exception:
        return ''


camera = cv2.VideoCapture(0)
# fps = int(camera.get(cv2.CAP_PROP_FPS))
fps = 31.8
w = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
fourcc = cv2.VideoWriter_fourcc(*'XVID')
# fourcc = cv2.VideoWriter_fourcc('m', 'p', '4', 'v')

P = pyaudio.PyAudio()
CHUNK = 1024*5
CHANNELS = 1
FORMAT = pyaudio.paInt16
RATE = 44100*4
stream = P.open(format=FORMAT, channels=CHANNELS, rate=RATE, frames_per_buffer=CHUNK, input=True, output=True)

frames = []
voices = []

while True:
    ret, frame = camera.read()
    frames.append(frame)
    if len(frames) > fps*6:
        frames.pop(0)

    input = stream.read(CHUNK, exception_on_overflow=False)
    voices.append(input)
    if len(voices) > fps*6:
        voices.pop(0)

    if waitKey(sys.stdin) == 'w':
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

        video_stream = ffmpeg.input(now+'-tmp.avi')
        audio_stream = ffmpeg.input(now+'-tmp.mp3')
        r_stream = ffmpeg.output(video_stream, audio_stream, 'result/'+now+'-result.mp4', vcodec="copy", acodec="aac")
        ffmpeg.run(r_stream)

        os.remove(now+'-tmp.avi')
        os.remove(now+'-tmp.wav')
        os.remove(now+'-tmp.mp3')
