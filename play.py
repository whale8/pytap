from pydub import AudioSegment
from pydub.utils import make_chunks
from pyaudio import PyAudio, paContinue
from pathlib import Path
from mutagen.flac import FLAC
from threading import Thread, Condition, Lock
import time
import struct
import math

# alsa message handling
from ctypes import (CFUNCTYPE, c_char_p, c_int, cdll) 
from contextlib import contextmanager


ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)

def py_error_handler(filename, line, function, err, fmt):
    pass

c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)

@contextmanager
def noalsaerr():
    try:
        asound = cdll.LoadLibrary('libasound.so')
        asound.snd_lib_error_set_handler(c_error_handler)
        yield
        asound.snd_lib_error_set_handler(None)
    except OSError:
        yield


class Song(Thread):
    def __init__(self, playlist, is_loop=False, *args, **kwargs):
        self.playlist = playlist
        self.playlist_len = len(playlist)
        self.play_number = 0
        self.play_count = 0
        self.__set_next_song()
        self.is_looped = is_loop
        self.is_paused = True
        self.is_stoped = True
        with noalsaerr():
            self.p = PyAudio()

        Thread.__init__(self, *args, **kwargs)
        self.pause_condition = Condition(Lock())
        #self.start()

    def pause(self):
        print('pause')
        self.is_paused = True
        self.is_stoped = True
        self.pause_condition.acquire()

    def play(self):
        self.is_paused = False
        self.is_stoped = False
        
        if not self._started.is_set():  # is not started
            self.start()
        else:  # restart
            self.pause_condition.notify()
            self.pause_condition.release()
    
    def stop(self):
        self.is_paused = False
        self.is_stoped = True

    def loop_on(self):
        self.is_looped = True

    def loop_off(self):
        self.is_looped = False
    
    def __set_next_song(self):
        self.play_number = self.play_count % self.playlist_len
        f = self.playlist[self.play_number]
        self.seg = AudioSegment.from_file(f)

    def __get_stream(self):
        return self.p.open(format=self.p.get_format_from_width(self.seg.sample_width),
                           channels=self.seg.channels,
                           rate=self.seg.frame_rate,
                           output=True) #, stream_callback=self.callback)

    def run(self):
        # loop playlist
        stream = self.__get_stream()
        chunk_count = 0
        chunks = make_chunks(self.seg, 100)
        
        while chunk_count < len(chunks):
            with self.pause_condition:
                while self.is_paused:
                    self.pause_condition.wait()

                data = (chunks[chunk_count])._data
                chunk_count += 1
                stream.write(data)

        stream.close()  # terminate the stream
        self.p.terminate()  # terminate the portaudio session

    def callback(self, in_data, frame_count, time_info, status):
        # bytes型を配列に変換する
        # (とりあえず8bit・モノクロだとした例を書く。
        # データは1バイトづつであり、0〜255までで中央値が128であることに注意)
        #print(in_data, frame_count, time_info, status)
        """
        in_data2 = struct.unpack(f'<{len(in_data)}B', in_data)
        in_data3 = tuple((x - 128) / 128.0 for x in in_data2)
        
        # 読み取った配列(各要素は-1以上1以下の実数)について、RMSを計算する
        rms = math.sqrt(sum([x * x for x in in_data3]) / len(in_data3))
        
        # RMSからデシベルを計算して表示する
        db = 20 * math.log10(rms) if rms > 0.0 else -math.inf
        print(f"RMS：{format(db, '3.1f')}[dB]")
        """
        return None, paContinue


if __name__ == "__main__":
    
    home = str(Path.home())  # ~は使えない
    file_name1 = home + "/Music/大貫妙子＆坂本龍一/UTAU/03 - 大貫妙子＆坂本龍一 - ３びきのくま.flac"
    file_name2 = home + "/Music/大貫妙子＆坂本龍一/UTAU/04 - 大貫妙子＆坂本龍一 - 赤とんぼ.flac"
    tags = FLAC(file_name1)
    print(tags)
    print(tags['title'][-1])
    #seg = pydub.AudioSegment.from_file(file_name, format='flac')
    #play(seg)
    
    # with this logic there is a short gap b/w files - os time to process,
    # trying to shorten gap by removing
    # 1 second from sleep time... works ok but will be system status 
    # dependent and may not work across runs??
    # Better would be to kill each tread when self._is_paused = True. 
    # I have a bunch of active threads piling up
    playlist = [file_name1, file_name2]
    song = Song(playlist)
    song.play()
    time.sleep(3)
    song.pause()
    time.sleep(3)
    song.play()
    #songLength = song.seg.duration_seconds
    #time.sleep(songLength - 1)  # daemon=Falseなのでsongだけが残ると終了する
