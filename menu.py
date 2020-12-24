import os
import curses
from curses import ascii


class CursesMenu:

    def __init__(self, options, h, w, y, x):
        self.screen = curses.newwin(h, w, y, x)
        self.options = options  # list
        self.selected_option = 0
        self.screen.keypad(1)

        # set up color pair for highlighted option
        curses.init_pair(5, curses.COLOR_BLACK, curses.COLOR_WHITE)
        self.hilite_color = curses.color_pair(5)
        self.normal_color = curses.A_NORMAL

    def prompt_selection(self, parent=None):
        option_count = len(self.options)
        input_key = None
        ENTER_KEY = ord('\n')
        while input_key != ENTER_KEY:

            # self.screen.border(0)
            for option in range(option_count):
                if self.selected_option == option:
                    self._draw_option(option, self.hilite_color)
                else:
                    self._draw_option(option, self.normal_color)

            max_y, max_x = self.screen.getmaxyx()
            if input_key is not None:
                self.screen.addstr(max_y - 3, max_x - 5,
                                   "{:3}".format(self.selected_option))
                self.screen.refresh()

            input_key = self.screen.getch()
            down_keys = [curses.KEY_DOWN,
                         ascii.SO,
                         ord('j')]
            up_keys = [curses.KEY_UP,
                       ascii.DLE,
                       ord('k')]
            exit_keys = [ord('q')]

            if input_key in down_keys:
                self.selected_option += 1

            if input_key in up_keys:
                self.selected_option -= 1

            self.selected_option %= option_count
            
            if input_key in exit_keys:
                self.selected_option = option_count
                # auto select exit and return
                break

        return self.selected_option

    def _draw_option(self, option_number, style):
        self.screen.addstr(1 + option_number, 1,
                           "{:3}: {}".\
                           format(option_number+1,
                                  self.options[option_number]),
                           style)

    def display(self):
        selected_option = self.prompt_selection()
        #i, _ = self.screen.getmaxyx()
        #curses.endwin()
        #os.system('clear')
        if selected_option < len(self.options):
            selected_opt = self.options[selected_option]
            return selected_opt


if __name__ == "__main__":
    curses.initscr()
    # init curses and curses input
    curses.noecho()
    curses.cbreak()
    curses.start_color()
    curses.curs_set(0)  # Hide cursor

    options = {'artist1' : ['album1', 'album2'],
               'artist2' : ['album1', 'album2', 'album3']}
    
    m = CursesMenu(list(options.keys()), 20, 20, 0, 0)

    selected_action = m.display()
    #os.system(selected_action['command'])
