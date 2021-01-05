import sys
import time
from datetime import timedelta
from threading import Thread
from math import ceil
import curses
from curses import wrapper
from curses import ascii

from play import Song, make_progressbar, db_visualizer
from get_files import get_files
from utils import TextWrapper

import locale
locale.setlocale(locale.LC_ALL, '')


class TuiAudioPlayer:

    def __init__(self, stdscr, artists, albums, songs):
        self.stdscr = stdscr
        self.artists = artists  # dict
        self.albums = albums  # dict
        self.songs = songs
        self.artists_list = list(self.artists.keys())
        
        self.state = 0  # [artist, album, song]
        self.selected_rows = [0, 0, 0]  # [artist, album, song]
        self.selected_names = [None, None, None]
        self.options = [{None:self.artists_list}, self.artists, self.albums]
        self.displayed_options = [self.artists_list, None, None]
        self.playing = False
        self.is_loop = False
        self.is_repeat = False
        self.song = None
        
        curses.noecho()  # キー入力を表示させない
        curses.cbreak()  # バッファを無効化(enterなしで反応する)
        curses.curs_set(0)  # カーソル無効化
        curses.start_color()
        curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_CYAN)  # for bkgd
        curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK) # for border
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_CYAN)  # highlite

        self.bkdg_color = curses.color_pair(1)
        self.border_color = curses.color_pair(2)
        self.hilite_color = curses.color_pair(3)
        self.normal_color = curses.A_NORMAL
                
        self.ENTER_KEYS = [curses.KEY_RIGHT,
                           ord('\n')]
        self.BACK_KEYS = [curses.KEY_BACKSPACE,  # not reliable
                          curses.KEY_LEFT,
                          ord('b')]
        self.DOWN_KEYS = [curses.KEY_DOWN,
                          ascii.SO,
                          ord('j')]
        self.UP_KEYS = [curses.KEY_UP,
                        ascii.DLE,
                        ord('k')]
        self.EXIT_KEYS = [ord('q')]
 
    def make_windows(self):
        self.max_row, self.max_col = self.stdscr.getmaxyx()
        artist_width = self.max_col // 3
        album_width = self.max_col // 3
        song_width = self.max_col - artist_width - album_width
        self.bottom_height = 6
        height = self.max_row - self.bottom_height
        
        
        self.artist_win = curses.newwin(height, artist_width - 1,
                                        1, 0)
        self.album_win = curses.newwin(height, album_width - 1,
                                       1, artist_width)
        self.song_win = curses.newwin(height, song_width,
                                      1, artist_width + album_width)
        self.border1 = curses.newwin(height, artist_width,
                                     1, 0)
        self.border2 = curses.newwin(height, album_width,
                                     1, artist_width)
        self.bottom_win = curses.newwin(self.bottom_height - 1, self.max_col,
                                        height + 2,  0)

        self.border1.border(" ", 0, " ", " ",
                            " ", curses.ACS_VLINE, " ", curses.ACS_VLINE)
        self.border2.border(" ", 0, " ", " ",
                            " ", curses.ACS_VLINE, " ", curses.ACS_VLINE)

        self.windows = [self.artist_win, self.album_win,
                        self.song_win, self.bottom_win]

        # pageupやカーソルキーを有効化
        self.stdscr.keypad(1)
        self.artist_win.keypad(1)
        self.album_win.keypad(1)
        self.song_win.keypad(1)
        self.bottom_win.keypad(1)

    def resize(self):
        is_resized = curses.is_term_resized(self.max_row, self.max_col)
        if is_resized:
            self.max_row, self.max_col = self.stdscr.getmaxyx()
            artist_width = self.max_col // 3
            album_width = self.max_col // 3
            song_width = self.max_col - artist_width - album_width
            height = self.max_row - 3
            self.stdscr.resize(self.max_row, self.max_col)
            self.artist_win.resize(height, artist_width - 1)
            self.album_win.resize(height, album_width - 1)
            self.song_win.resize(height, song_width)
            self.border1.resize(height, artist_width)
            self.border2.resize(height, album_width)

            self.album_win.mvwin(1, artist_width)
            self.song_win.mvwin(1, artist_width + album_width)
            self.border2.mvwin(1, artist_width)

            self.clear()
            for state in range(self.state):
                self.draw_options(state)

            self.refresh()

    def clear(self):
        self.stdscr.clear()
        self.border1.clear()
        self.border2.clear()
        self.border1.border(" ", 0, " ", " ",
                            " ", curses.ACS_VLINE, " ", curses.ACS_VLINE)
        self.border2.border(" ", 0, " ", " ",
                            " ", curses.ACS_VLINE, " ", curses.ACS_VLINE)
        self.artist_win.clear()
        self.album_win.clear()
        self.song_win.clear()
        self.bottom_win.clear()

    def refresh(self):
        self.stdscr.refresh()
        self.border1.refresh()
        self.border2.refresh()
        self.artist_win.refresh()
        self.album_win.refresh()
        self.song_win.refresh()
        self.bottom_win.refresh()

    def render_bottom(self):
        while self.playing:
            duration = self.song.duration
            rate = self.song.rate
            channels = self.song.channels
            sample_width = self.song.sample_width
            title = self.song.title
            album = self.song.album
            artist = self.song.artist
            db = self.song.db
            max_db = self.song.max_db
            progress = self.song.progress
            progress_bar = make_progressbar(progress)
            time_elapsed = int(self.song.chunk_count * self.song.chunk_ms / 1000)
            time_left = int(duration) - time_elapsed

            info1 = f"    Duration: {timedelta(seconds=int(duration))}\t" \
                f" Title: {title}\n" \
                f"Samplingrate: {rate} Hz\t" \
                f" Album: {album}\n" \
                f"    Channels: {channels} @ {sample_width*8}bit\t" \
                f"Artist: {artist}"

            info2 = f"\r[{progress_bar}] {progress*100:5.2f}% " \
                f"{timedelta(seconds=time_elapsed)} " \
                f"[{timedelta(seconds=time_left)}] " \
                f"[{db_visualizer(db, max_db)}]"

            self.bottom_win.erase()
            time.sleep(0.25)
            self.bottom_win.addstr(0, 0,
                                   info1)
            self.bottom_win.addstr(3, 0, info2)
            self.bottom_win.refresh()
        
    def draw_options(self, state):
        attention_window = self.windows[state]
        attention_options = self.displayed_options[state]
        rows_per_page, max_col = attention_window.getmaxyx()
        rows_per_page -= 2
        w = TextWrapper(width=max_col-9)  # minus error
        max_page = ceil(len(attention_options) / rows_per_page)
        q, mod = divmod(self.selected_rows[state], rows_per_page)
        start = q*rows_per_page
        end = start + rows_per_page
        attention_window.erase()
        top_message = f"page {q+1} / {max_page}"
        attention_window.addstr(0, max_col-len(top_message), top_message)
        
        for i, option in enumerate(attention_options[start:end]):
            if i == mod:
                attention_window.addstr(i + 1, 1,
                                        f"{i+1:3}: {w.shorten(option)}",
                                        self.hilite_color)
            else:
                attention_window.addstr(i + 1, 1,
                                        f"{i+1:3}: {w.shorten(option)}",
                                        self.normal_color)

    def run(self):
        # Start windows
        self.make_windows()
        self.stdscr.bkgd(self.bkdg_color)
        self.border2.bkgd(self.border_color)
        self.border1.bkgd(self.border_color)
        self.refresh()

        # main loop
        # stateの変更は全部ここでする
        while True:
            # stateの応じた選択画面の表示
            input_key = self.prompt_selection()
            if input_key in self.ENTER_KEYS:
                selected_name = self.selected_names[self.state]

                if self.state == 2:
                    if not self.playing:
                        playlist = [self.songs[selected_name]]
                        self.song = Song(playlist)
                        self.song.play()
                    else:
                        self.playing = False  # terminate p
                        self.song.pause()
                        playlist = [self.songs[selected_name]]
                        self.song = Song(playlist)
                        self.song.play()
                    
                    self.playing = True
                    self.p = Thread(target=self.render_bottom)
                    self.p.setDaemon(True)
                    self.p.start()
                        
                else:
                    self.state += 1
                    self.displayed_options[self.state] \
                        = self.options[self.state][selected_name]
                
            else:
                self.selected_rows[self.state] = 0
                self.state = max(0, self.state - 1)
                
    def prompt_selection(self):

        options = self.displayed_options[self.state] #attention_options
        attention_window = self.windows[self.state]
        option_count = len(options)
        input_key = None
        
        while input_key not in self.ENTER_KEYS + self.BACK_KEYS:

            self.resize()
            self.draw_options(self.state)

            max_y, max_x = attention_window.getmaxyx()
            """
            if input_key is not None:
                attention_window.addstr(max_y - 5, max_x - 5,
                                        f"state {self.state:3}")
                attention_window.addstr(max_y - 4, max_x - 5,
                                        f"0 {self.selected_rows[0]:3}")
                attention_window.addstr(max_y - 3, max_x - 5,
                                        f"1 {self.selected_rows[1]:3}")
                attention_window.addstr(max_y - 2, max_x - 5,
                                        f"2 {self.selected_rows[2]:3}")
                attention_window.refresh()
            """
            input_key = attention_window.getch()

            if input_key in self.DOWN_KEYS:
                self.selected_rows[self.state] += 1

            if input_key in self.UP_KEYS:
                self.selected_rows[self.state] -= 1
                
            self.selected_rows[self.state] %= option_count
            
            if input_key in self.EXIT_KEYS:
                self.finish()
                sys.exit(0)

            if input_key in self.ENTER_KEYS:
                self.selected_names[self.state] \
                    = options[self.selected_rows[self.state]]
                break

            if input_key in self.BACK_KEYS:
                attention_window.clear()
                attention_window.refresh()
                break

        return input_key

    def finish(self):
        # 終了処理
        if self.song != None:
            self.song.terminate()

        curses.nocbreak()  # 元の設定に戻す
        curses.echo()  # 元の設定に戻す
        curses.endwin()

def main(stdscr):
    artists, albums, songs = get_files()
    tap = TuiAudioPlayer(stdscr, artists, albums, songs)
    tap.run()
    
if __name__ == "__main__":
    stdscr = curses.initscr()
    wrapper(main)

