import time
from datetime import timedelta
from pathlib import Path
from threading import Thread, Condition, Lock

from pydub import AudioSegment
from pydub.utils import make_chunks
from pyaudio import PyAudio, paInt8, paInt16, paInt24, paInt32
from mutagen.flac import FLAC

# alsa message handling
from ctypes import (CFUNCTYPE, c_char_p, c_int, cdll) 
from contextlib import contextmanager

from get_files import get_attribute


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
        self.progress = 0
        self.db = 0
        self.max_db = 0
        self.duration = 0
        self.rate = 0
        self.channels = 0
        self.sample_width = 0
        self.title = ""
        self.artist = ""
        self.album = ""
        self.track = ""
        self.chunk_ms = 100  # 100 millisec
        self.chunk_count = 0
        with noalsaerr():
            self.p = PyAudio()

        Thread.__init__(self, *args, **kwargs)
        self.daemon = True  # mainスレッドが終了した場合に終わるように
        # Songクラス単体で使うならFalseにするか，time.sleep(duration)
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

    def volume(self, decibel):  # 音割れする，別の手法にすべきか
        self.pause()  # underrun 防止
        self.__set_segment()
        self.seg += decibel
        self.chunks = make_chunks(self.seg, self.chunk_ms)
        self.__set_stream()
        self.play()

    def mute(self):
        pass

    def get_info(self):  # set_info?
        duration = self.seg.duration_seconds  # 再生時間
        rate = self.seg.frame_rate  # サンプリングレート
        channels = self.seg.channels  # (1:mono, 2:stereo)
        sample_width = self.seg.sample_width  # byte
        return (duration, rate, channels, sample_width)

    def get_playback_info(self):
        return (self.progress, self.db)
    
    def __set_segment(self):

        self.play_number = self.play_count % len(self.playlist)
        f = self.playlist[self.play_number]
        tags = FLAC(f)
        
        self.title = get_attribute(tags, 'title')  # tags.get(key, None)もあり
        self.album = get_attribute(tags, 'album')
        self.artist = get_attribute(tags, 'albumartist')
        if self.artist == None:
            self.artist = get_attribute(tags, 'artist')
        self.track = get_attribute(tags, 'tracknumber')
        self.seg = AudioSegment.from_file(f)

    def __set_stream(self):
        # format は portaudio の定数
        # (paInt8=16, paInt16=8, paInt24=4, paInt32=2, paFloat32=1)のどれか
        # pydub.AudioSegment.sample_width も量子化ビット数を返す
        # (1=8bit, 2=16bit, 3?, 4=32bit)
        # PyAudio.get_format_from_width は paInt32 を返さない
        # 手持ちの音源で 32bit-float がないので即時療法で対処
        # https://github.com/jleb/pyaudio/blob/0109cc46cac6a3c404050f4ba11752e51aeb1fda/src/pyaudio.py#L215
        # issue 案件な気がする
        def get_format_from_width(width):
            if width == 1:
                return paInt8  # = 16
            elif width == 2:
                return paInt16  # = 8
            elif width == 3:
                return paInt24  # = 4
            elif width == 4:
                return paInt32  # = 2
            else:
                raise ValueError(f"Invalid width {width}")
        
        self.stream = self.p.open(format
                                  =get_format_from_width(
                                      self.seg.sample_width),
                                  #=self.p.get_format_from_width(
                                  #    self.seg.sample_width),
                                  channels=self.seg.channels,
                                  rate=self.seg.frame_rate,
                                  output=True)#, stream_callback=self.callback)

    def __play_song(self):
        self.__set_segment()
        self.chunks = make_chunks(self.seg, self.chunk_ms)
        self.chunk_count = 0
        self.__set_stream()
        self.duration = self.seg.duration_seconds  # 再生時間
        self.rate = self.seg.frame_rate  # サンプリングレート
        self.channels = self.seg.channels  # (1:mono, 2:stereo)
        self.sample_width = self.seg.sample_width  # byte (1:8bit, 2:16bit ...)
        self.max_db = self.seg.max_dBFS

        while not self.is_stoped:
            if self.chunk_count >= len(self.chunks):  # 最後まで再生して終了
                self.play_count += 1  # next song
                break
            
            with self.pause_condition:
                chunk = self.chunks[self.chunk_count]
                data = chunk._data
                self.chunk_count += 1
                self.db = chunk.dBFS
                self.progress = self.chunk_count/len(self.chunks)
                self.stream.write(data)
                
                while self.is_paused:
                    self.stream.stop_stream()
                    # ALSA lib pcm.c:8526:(snd_pcm_recover) underrun occurred
                    self.pause_condition.wait()
                    self.stream.start_stream()  # resume
        
        self.stream.close()  # terminate the stream


    def run(self):
        # loop playlist
        while self.play_count < len(self.playlist) \
              or self.is_looped or not self.is_terminated:
            with self.stop_condition:
                self.__play_song()

                while self.is_stoped:
                    self.stop_condition.wait()

        self.p.terminate()  # terminate the portaudio session


def make_progressbar(progress):
    # progress [0, 1]
    num = 10
    p = int(progress*100//num)
    return '=' * p + ' ' * (10 - p)

def spectrogram():
    pass

def db_visualizer(db, max_db):
    count = 10
    db -= max_db
    db += count * 10
    if db > 0:
        q, mod = divmod(db, 10)
        if mod > 5:
            v = "=" * int(q) + "-" + " " * (count-1-int(q))
        else:
            v = "=" * int(q) + " " * (count-int(q))
    else:
        v = " " * count
    return v

if __name__ == "__main__":
    
    home = str(Path.home())  # ~は使えない
    file_name1 = home + "/Music/大貫妙子＆坂本龍一/UTAU/03 - 大貫妙子＆坂本龍一 - ３びきのくま.flac"
    file_name2 = home + "/Music/大貫妙子＆坂本龍一/UTAU/04 - 大貫妙子＆坂本龍一 - 赤とんぼ.flac"
    #tags = FLAC(file_name1)
    #print(tags)
    #print(tags['title'][-1])
    #seg = pydub.AudioSegment.from_file(file_name1, format='flac')
    #play(seg)

    input_file = "/media/whale/Extreme SSD/Kevin Penkin/「メイドインアビス」O．S．T．/TVアニメ メイドインアビス オリジナルサウンドトラッ_01_Made in Abyss.flac"
    playlist = [input_file, file_name1, file_name2]
    song = Song(playlist)
    song.play()
    time.sleep(1)
    duration, rate, channels, sample_width = song.get_info()
    print(song.sample_width)
    print(1, song.p.get_format_from_width(1))
    print(2, song.p.get_format_from_width(2))
    print(3, song.p.get_format_from_width(3))
    print(4, song.p.get_format_from_width(4))
    print(f"    Duration: {timedelta(seconds=int(song.duration))}\t"
          f" Title: {song.title}\n"
          f"Samplingrate: {song.rate} Hz\t"
          f" Album: {song.album}\n"
          f"    Channels: {song.channels} @ {song.sample_width*8}bit\t"
          f"Artist: {song.artist}")
    while True:
        time.sleep(0.02)
        progress_bar = make_progressbar(song.progress)
        time_elapsed = int(song.chunk_count * song.chunk_ms / 1000)
        time_left = int(song.duration) - time_elapsed
        print(f"\r[{progress_bar}] {song.progress*100:5.2f} % " +
              f"{timedelta(seconds=time_elapsed)} " +
              f"[{timedelta(seconds=time_left)}] " +
              f"{db_visualizer(song.db, song.max_db)}", end="")
        
    time.sleep(5)
    print("volume")
    song.volume(1)
    time.sleep(180)
    print("volume")
    song.volume(1)
    time.sleep(5)
    print("volume")
    song.volume(-1)
    time.sleep(5)
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
