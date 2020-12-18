from pydub import AudioSegment
from pydub.utils import make_chunks
from pyaudio import PyAudio
from pathlib import Path
from mutagen.flac import FLAC
from threading import Thread
import time

# alsa message handling
from ctypes import *
from contextlib import contextmanager


ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)

def py_error_handler(filename, line, function, err, fmt):
    pass

c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)

@contextmanager
def noalsaerr():
    asound = cdll.LoadLibrary('libasound.so')
    asound.snd_lib_error_set_handler(c_error_handler)
    yield
    asound.snd_lib_error_set_handler(None)



class Song(Thread):
    def __init__(self, f, *args, **kwargs):
        self.seg = AudioSegment.from_file(f)
        self.__is_paused = True
        with noalsaerr():
            self.p = PyAudio()

        Thread.__init__(self, *args, **kwargs)
        self.start()

    def pause(self):
        self.__is_paused = True

    def play(self):
        self.__is_paused = False

    def __get_stream(self):
        return self.p.open(format=self.p.get_format_from_width(self.seg.sample_width),
                           channels=self.seg.channels,
                           rate=self.seg.frame_rate,
                           output=True)

    def run(self):
        stream = self.__get_stream()
        chunk_count = 0
        chunks = make_chunks(self.seg, 100)
        while chunk_count < len(chunks) and not self.__is_paused:
            data = (chunks[chunk_count])._data
            chunk_count += 1
            stream.write(data)

        stream.stop_stream()
        self.p.terminate()


if __name__ == "__main__":
    
    home = str(Path.home())  # ~は使えない
    file_name = home + "/Music/大貫妙子＆坂本龍一/UTAU/03 - 大貫妙子＆坂本龍一 - ３びきのくま.flac"
    tags = FLAC(file_name)
    print(tags)
    #seg = pydub.AudioSegment.from_file(file_name, format='flac')
    #play(seg)
    
    # with this logic there is a short gap b/w files - os time to process,
    # trying to shorten gap by removing
    # 1 second from sleep time... works ok but will be system status 
    # dependent and may not work across runs??
    # Better would be to kill each tread when self._is_paused = True. 
    # I have a bunch of active threads piling up
    song = Song(file_name)
    song.play()
    songLength = song.seg.duration_seconds
    time.sleep(songLength - 1)
