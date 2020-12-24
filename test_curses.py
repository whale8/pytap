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
from menu import CursesMenu

import locale
locale.setlocale(locale.LC_ALL, '')

sleep_time = 1/24
home = str(Path.home())  # ~は使えない
# files = [p for p in glob(home + '/Music/**/*', recursive=True)
#         if re.search('/*\.(flac|wav)\Z', str(p))]

files = [p for p in glob(home + '/Music/**/*', recursive=True)
         if re.search('/*\.flac\Z', str(p))]
artists = set(FLAC(f)['artist'][-1] for f in files)

# python 3.7 移行はdictも順序を保持する
tree1 = {FLAC(f)['artist'][-1]: FLAC(f)['album'][-1] for f in files}
tree2 = {FLAC(f)['album'][-1]: FLAC(f)['title'][-1] for f in files}

tree2 = dict()
for f in files:
    tree2.setdefault(FLAC(f)['album'][-1], []).append(FLAC(f)['title'][-1])

print(tree1)
print(tree2)


def main(stdscr):
    highlight_text = curses.color_pair(1)
    normal_text = curses.A_NORMAL

    #stdscr.clear()
    stdscr.bkgd(curses.color_pair(1))  # 全体の背景
    
    max_row, max_col = stdscr.getmaxyx()
    l_width = max_col//3
    r_width = max_col - l_width
    height = max_row - 3

    # border, 中央の間仕切り用のwindow
    border = curses.newwin(height, l_width, 1, 0)
    border.bkgd(curses.color_pair(2))
    border.border(" ", 0, " ", " ", " ", curses.ACS_VLINE, " ", curses.ACS_VLINE)
    
    # left, artist
    """
    left_win = curses.newwin(height, l_width - 1, 1, 0)
    for i, artist in enumerate(tree1.keys()):
        left_win.addstr(i+1, 0,
                        "{}".format(artist))
    """
    left_win = CursesMenu(list(tree1.keys()), height, l_width - 1, 1, 0)
    
    song = Song(files[-1])
    song.play()
    #songLength = song.seg.duration_seconds
    #time.sleep(songLength - 1)

    # right, track
    right_win = curses.newwin(height, r_width, 1, l_width)
    for i, album in enumerate(tree2.keys()):
        right_win.addstr(i+1, 0,
                         "{}".format(album))
    
    stdscr.refresh()
    border.refresh()
    #left_win.move(0, 0)
    #left_win.refresh()
    right_win.refresh()
    windows_list = [stdscr, border, left_win, right_win]

    while True:
        left_win.display()
        cursor_y, cursor_x = stdscr.getyx()
        is_resized = curses.is_term_resized(max_row, max_col)
        if is_resized:
            max_row, max_col = stdscr.getmaxyx()
            l_width = max_col//3
            r_width = max_col - l_width
            height = max_row - 3
            stdscr.resize(max_row, max_col)
            border.resize(height, l_width)
            left_win.resize(height, l_width - 1)
            right_win.resize(height, r_width)
            right_win.mvwin(1, l_width)

            stdscr.clear()
            border.clear()
            left_win.clear()
            right_win.clear()
            border.border(" ", 0, " ", " ", " ", curses.ACS_VLINE, " ", curses.ACS_VLINE)

        key = stdscr.getch()

        if key == ord('q'):
            break
        """
        elif key == ascii.SO or key == curses.KEY_DOWN:
            cursor_y = min(max_row - 1, cursor_y + 1)
        elif key == ascii.DLE or key == curses.KEY_UP:
            cursor_y = max(0, cursor_y - 1)
        """

        stdscr.move(cursor_y, cursor_x)
        #left_win.addstr(0, 0, f"{cursor_y},{cursor_x}")
        #left_win.addstr(1, 0, f"{max_row},{max_col}")
        
        time.sleep(sleep_time)

        if stdscr.is_wintouched():
            stdscr.refresh()
        if border.is_wintouched():
            border.refresh()
        #if left_win.is_wintouched():
        #    left_win.refresh()
        if right_win.is_wintouched():
            right_win.refresh()

    song.pause()
    curses.echo()
    curses.endwin()
            

if __name__ == "__main__":
    curses.initscr()  # これを呼んだ後じゃないといろいろ使えない

    # Start colors in curses
    curses.noecho()
    curses.cbreak()
    curses.start_color()
    curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_CYAN)
    curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)

    wrapper(main)

    
