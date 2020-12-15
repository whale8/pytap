import os
import re
import glob
from pathlib import Path
import curses
from curses import wrapper
import curses.ascii
import locale
locale.setlocale(locale.LC_ALL, '')
# files = os.listdir('~/Music/*/*wav')
home = str(Path.home())  # ~は使えない
files = glob.glob(home+'/Music/**/*.wav', recursive=True)

def main(stdscr):
    # Start colors in curses
    curses.start_color()
    curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_CYAN)
    curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)

    highlight_text = curses.color_pair(1) # 上の行のpair idを使う
    normal_text = curses.A_NORMAL

    stdscr.clear()
    stdscr.bkgd(curses.color_pair(1))  # 全体の背景
    stdscr.refresh()
    stdscr.getkey()

    curses.curs_set(0)  # カーソル
    max_row, max_col = stdscr.getmaxyx()
    
    # left, artist
    left_win = curses.newwin(max_row-2, max_col//2 - 1, 1, 0)
    # left_win.border(0, 0, 0, 0)
    left_win.clear()
    left_win.addstr(0, 0, "{}, {}".format(max_row, max_col),
                    curses.color_pair(3))
    for i, f in enumerate(files):
        left_win.addstr(i+1, 1,
                        "{}".format(f))

    left_win.refresh()
    left_win.getkey()

    # right, track
    right_win = curses.newwin(max_row-2, max_col//2 - 1 , 1, max_col//2)
    right_win.clear()
    right_win.refresh()
    right_win.getkey()

    curses.echo()
    curses.endwin()


if __name__ == "__main__":
    curses.initscr()  # これを呼んだ後じゃないといろいろ使えない
    wrapper(main)
