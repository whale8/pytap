import os
import re
from glob import glob
from pathlib import Path
import time
import curses
from curses import wrapper
from curses import ascii
from mutagen.flac import FLAC

from play import Song

import locale
locale.setlocale(locale.LC_ALL, '')

sleep_time = 1/24
home = str(Path.home())  # ~は使えない
files = [p for p in glob(home + '/Music/**/*', recursive=True)
         if re.search('/*\.(flac|wav)\Z', str(p))]
artists = set(FLAC(f)['artist'][-1] for f in files)



def main(stdscr):
    # Start colors in curses
    curses.start_color()
    curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_CYAN)
    curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)

    highlight_text = curses.color_pair(1)
    normal_text = curses.A_NORMAL

    #stdscr.clear()
    stdscr.bkgd(curses.color_pair(1))  # 全体の背景
    

    curses.curs_set(0)  # カーソル
    max_row, max_col = stdscr.getmaxyx()
    l_width = max_col//3
    r_width = max_col - l_width
    height = max_row - 3

    # border, 中央の間仕切り用のwindow
    border = curses.newwin(height, l_width, 1, 0)
    border.bkgd(curses.color_pair(2))
    border.border(" ", 0, " ", " ", " ", curses.ACS_VLINE, " ", curses.ACS_VLINE)
    

    # left, artist
    left_win = curses.newwin(height, l_width - 1, 1, 0)
    #left_win.clear()
    for i, artist in enumerate(artists):
        left_win.addstr(i+1, 0,
                        "{}".format(artist))

    song = Song(files[-1])
    song.play()
    #songLength = song.seg.duration_seconds
    #time.sleep(songLength - 1)


    # right, track
    right_win = curses.newwin(height, r_width, 1, l_width)
    #right_win.clear()

    stdscr.refresh()
    border.refresh()
    left_win.refresh()
    right_win.refresh()

    while True:
        key = stdscr.getch()

        if key == ord('q'):
            break

        time.sleep(sleep_time)

    song.pause()
    curses.echo()
    curses.endwin()
            

if __name__ == "__main__":
    curses.initscr()  # これを呼んだ後じゃないといろいろ使えない
    wrapper(main)
