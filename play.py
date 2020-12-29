import time
from pathlib import Path
from threading import Thread, Condition, Lock

from pydub import AudioSegment
from pydub.utils import make_chunks
from pyaudio import PyAudio
from mutagen.flac import FLAC

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
        self.play_number = 0
        self.play_count = 0
        self.is_looped = is_loop
        self.is_paused = True
        self.is_stoped = True
        self.is_terminated = True
        with noalsaerr():
            self.p = PyAudio()

        Thread.__init__(self, *args, **kwargs)
        self.daemon = True
        self.pause_condition = Condition(Lock())
        self.stop_condition = Condition(Lock())

    def pause(self):  # 再生状況を保存
        self.is_paused = True
        self.pause_condition.acquire()

    def stop(self):  # 再生中の曲番号だけ保存，再生状況は保存しない
        self.is_stoped = True
        self.stop_condition.acquire()

    def play(self):
        if not self._started.is_set():  # is not started
            self.start()
        else:  # restart
            if self.is_stoped:
                self.stop_condition.notify()
                self.stop_condition.release()
            if self.is_paused:
                self.pause_condition.notify()
                self.pause_condition.release()            

        self.is_paused = False
        self.is_stoped = False

    def terminate(self):
        self.is_terminated = True
        
    def skip(self):
        self.stop()
        self.play_count += 1
        self.play()

    def rewind(self):
        self.stop()
        self.play_count = min(0, self.play_count - 1)
        self.play()

    def loop_on(self):
        self.is_looped = True

    def loop_off(self):
        # offにしてもplaylistの現在の曲から最後までは演奏する
        self.play_count = self.play_count % len(self.playlist)
        self.is_looped = False
    
    def __set_segment(self):
        self.play_number = self.play_count % len(self.playlist)
        f = self.playlist[self.play_number]
        self.seg = AudioSegment.from_file(f)

    def __get_stream(self):
        return self.p.open(format=self.p.get_format_from_width(self.seg.sample_width),
                           channels=self.seg.channels,
                           rate=self.seg.frame_rate,
                           output=True) #, stream_callback=self.callback)

    def __play_song(self):
        self.__set_segment()
        stream = self.__get_stream()
        chunk_count = 0
        chunks = make_chunks(self.seg, 100)
        
        while not self.is_stoped:
            if chunk_count >= len(chunks):  # 最後まで再生して終了
                self.play_count += 1  # next song
                break
            
            with self.pause_condition:
                data = (chunks[chunk_count])._data
                chunk_count += 1
                stream.write(data)
                
                while self.is_paused:
                    stream.stop_stream()
                    # ALSA lib pcm.c:8526:(snd_pcm_recover) underrun occurred
                    self.pause_condition.wait()
                    stream.start_stream()  # resume

        stream.close()  # terminate the stream
        
    def run(self):
        # loop playlist
        while self.play_count < len(self.playlist) \
              or self.is_looped or not self.is_terminated:
            with self.stop_condition:
                self.__play_song()
                while self.is_stoped:
                    self.stop_condition.wait()

        self.p.terminate()  # terminate the portaudio session


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
    print('pause')
    song.pause()
    time.sleep(3)
    song.play()
    time.sleep(3)
    print('stop')
    song.stop()
    time.sleep(3)
    song.play()
    print('skip')
    song.skip()
    time.sleep(3)
    print('rewind')
    song.rewind()
    print('skip')
    song.skip()
    time.sleep(3)
    song.loop_on()
    print('skip')
    song.skip()
    time.sleep(3)
    
    #songLength = song.seg.duration_seconds
    #time.sleep(songLength - 1)  # daemon=Falseなのでsongだけが残ると終了する
