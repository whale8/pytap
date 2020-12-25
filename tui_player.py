import os
import sys
import re
from glob import glob
from pathlib import Path
import time
import curses

from curses import wrapper
from curses import ascii
from mutagen.flac import FLAC

from play import Song
from menu import CursesMenu

import locale
locale.setlocale(locale.LC_ALL, '')

sleep_time = 1/24
home = str(Path.home())  # ~は使えない

# files = [p for p in glob(home + '/Music/**/*', recursive=True)
#         if re.search('/*\.(flac|wav)\Z', str(p))]

files = [p for p in glob(home + '/Music/**/*', recursive=True)
         if re.search('/*\.flac\Z', str(p))]

tree1 = dict()
tree2 = dict()
tree3 = dict()
for f in files:
    artist = FLAC(f)['artist'][-1]
    album = FLAC(f)['album'][-1]
    title = FLAC(f)['title'][-1]
    
    if (artist not in tree1) \
       or (artist in tree1 and album not in tree1[artist]):
        tree1.setdefault(artist, []).append(album)
        
    if (album not in tree2) \
       or (album in tree2 and album not in tree2[album]):
        tree2.setdefault(album, []).append(title)

    tree3.setdefault(title, f)

print(tree1)
print(tree2)
print(tree3)


class TuiAudioPlayer:

    # 継承書きたいけどwindow objec見つからない
    def __init__(self, artists, albums, songs):
        
        self.artists = artists  # dict
        self.albums = albums  # dict
        self.songs = songs
        self.artists_list = list(self.artists.keys())
        self.albums_list = list(self.albums.keys())

        self.status = 0  # [artist, album, song]
        self.selected_artist = 0
        self.selected_album = 0
        self.selected_song = 0
        self.playing = False
        self.song = None
        
        # Start windows
        self.make_windows()

        curses.noecho()
        curses.cbreak()
        curses.curs_set(0)
        curses.start_color()
        curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_CYAN)  # for bkgd
        curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK) # for border
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_CYAN)  # highlite

        self.bkdg_color = curses.color_pair(1)
        self.border_color = curses.color_pair(2)
        self.hilite_color = curses.color_pair(3)
        self.normal_color = curses.A_NORMAL
        
        self.stdscr.bkgd(self.bkdg_color)
        self.border2.bkgd(self.border_color)
        self.border1.bkgd(self.border_color)
        
        self.ENTER_KEY = ord('\n')
        self.DOWN_KEYS = [curses.KEY_DOWN,
                          ascii.SO,
                          ord('j')]
        self.UP_KEYS = [curses.KEY_UP,
                        ascii.DLE,
                        ord('k')]
        self.EXIT_KEYS = [ord('q')]
        
        self.refresh()
        
    def make_windows(self):
        self.stdscr = curses.initscr()
        max_row, max_col = self.stdscr.getmaxyx()
        artist_width = max_col // 3
        album_width = max_col // 3
        song_width = max_col - artist_width - album_width
        height = max_row - 3
        
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

        self.border1.border(" ", 0, " ", " ",
                            " ", curses.ACS_VLINE, " ", curses.ACS_VLINE)
        self.border2.border(" ", 0, " ", " ",
                            " ", curses.ACS_VLINE, " ", curses.ACS_VLINE)

        self.stdscr.keypad(1)
        self.artist_win.keypad(1)
        self.album_win.keypad(1)
        self.song_win.keypad(1)

    def resize(self):
        pass

    def refresh(self):
        self.stdscr.refresh()
        self.border1.refresh()
        self.border2.refresh()
        self.artist_win.refresh()
        self.album_win.refresh()
        self.song_win.refresh()

    def run(self):
        while True:
            select_key = self.prompt_selection()
            if self.status == 0:
                self.status = 1
                self.selected_album = 0
            elif self.status == 1:
                self.status = 2
                self.selected_song = 0
            else:
                self.song = Song(self.songs[select_key])
                self.song.play()
                self.playing = True
                
    def prompt_selection(self):
        if self.status == 0:
            self.options = self.artists_list
            selected_option = self.selected_artist
            self.attention_screen = self.artist_win
        elif self.status == 1:
            self.options = self.artists[
                self.artists_list[self.selected_artist]]
            selected_option = self.selected_album
            self.attention_screen = self.album_win
        else:
            self.options = self.albums[
                self.albums_list[self.selected_album]]
            selected_option = self.selected_song
            self.attention_screen = self.song_win

        option_count = len(self.options)
        input_key = None
        
        while input_key != self.ENTER_KEY:

            for option in range(option_count):
                if selected_option == option:
                    self._draw_option(option, self.hilite_color)
                else:
                    self._draw_option(option, self.normal_color)

            max_y, max_x = self.attention_screen.getmaxyx()
            if input_key is not None:
                self.attention_screen.addstr(max_y - 3, max_x - 5,
                                             "{:3}".format(selected_option))
                self.attention_screen.refresh()

            input_key = self.attention_screen.getch()

            if input_key in self.DOWN_KEYS:
                selected_option += 1

            if input_key in self.UP_KEYS:
                selected_option -= 1

            selected_option %= option_count
            
            if input_key in self.EXIT_KEYS:
                self.finish()
                sys.exit(0)
                # break
                # return None


        if self.status == 0:
            self.selected_artist = selected_option
        elif self.status == 1:
            self.selected_album = selected_option
        else:
            self.selected_song = selected_option
            
        return self.options[selected_option]

    def _draw_option(self, option_number, style):
        self.attention_screen.addstr(1 + option_number, 1,
                                     "{:3}: {}".\
                                     format(option_number+1,
                                            self.options[option_number]),
                                     style)

    def finish(self):
        if self.playing:
            self.song.pause()

        curses.echo()
        curses.endwin()

def main(stdscr):
    tap = TuiAudioPlayer(tree1, tree2, tree3)
    tap.run()

if __name__ == "__main__":
    wrapper(main)

