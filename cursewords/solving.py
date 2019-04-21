#! /usr/bin/env python3

"""
Control flow for solving mode
"""

# pylint: disable=bare-except
# pylint: disable=no-self-use
# pylint: disable=too-many-arguments
# pylint: disable=too-many-boolean-expressions
# pylint: disable=too-many-branches
# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-lines
# pylint: disable=too-many-locals
# pylint: disable=too-many-public-methods
# pylint: disable=too-many-statements
# pylint: disable=undefined-variable

import argparse
import itertools
import os
import sys
import time
import textwrap
import threading

import puz

from blessed import Terminal


class Cursor:
    """ This class represents our cursor and active region """

    def __init__(self, position, direction, grid):
        self.position = position
        self.direction = direction
        self.grid = grid

    def switch_direction(self, to=None):
        # pylint: disable=invalid-name
        """ switch from down to across or vice-versa """
        if to:
            self.direction = to
        elif self.direction == "across":
            self.direction = "down"
        elif self.direction == "down":
            self.direction = "across"

    def advance(self):
        """ move forward """
        if self.direction == "across":
            self.position = self.move_right()
        elif self.direction == "down":
            self.position = self.move_down()

    def retreat(self):
        """ move backward """
        if self.direction == "across":
            self.position = self.move_left()
        elif self.direction == "down":
            self.position = self.move_up()

    def advance_perpendicular(self):
        """ move forward along the oposite access as our orientation """
        self.switch_direction()
        self.advance()
        self.switch_direction()

    def retreat_perpendicular(self):
        """ move backward along the oposite access as our orientation """
        self.switch_direction()
        self.retreat()
        self.switch_direction()

    def advance_within_word(self, overwrite_mode=False, wrap_mode=False):
        """ move forward within a word """
        within_pos = self.move_within_word(overwrite_mode, wrap_mode)
        if within_pos:
            self.position = within_pos
        else:
            self.advance_to_next_word(blank_placement=True)

    def move_within_word(self, overwrite_mode=False, wrap_mode=False):
        """ move arbitrarily within a word """
        word_spaces = self.current_word()
        current_space = word_spaces.index(self.position)
        ordered_spaces = word_spaces[current_space + 1:]

        if wrap_mode:
            ordered_spaces += word_spaces[:current_space]

        if not overwrite_mode:
            ordered_spaces = [pos for pos in ordered_spaces
                              if self.grid.cells.get(pos).is_blankish]

        return next(iter(ordered_spaces), None)

    def retreat_within_word(self, end_placement=False, blank_placement=False):
        """ move backward within a word """
        pos_index = self.current_word().index(self.position)
        earliest_blank = self.earliest_blank_in_word()

        if (blank_placement and
                earliest_blank and
                pos_index > self.current_word().index(earliest_blank)):
            self.position = earliest_blank
        elif not blank_placement and pos_index > 0:
            self.position = self.current_word()[pos_index - 1]
        else:
            self.retreat_to_previous_word(end_placement, blank_placement)

    def advance_to_next_word(self, blank_placement=False):
        """ move forward to next word """
        if self.direction == "across":
            word_group = self.grid.across_words
            next_words = self.grid.down_words_grouped
        elif self.direction == "down":
            word_group = self.grid.down_words_grouped
            next_words = self.grid.across_words

        word_index = word_group.index(self.current_word())

        if word_index == len(word_group) - 1:
            self.switch_direction()
            self.position = next_words[0][0]
        else:
            self.position = word_group[word_index + 1][0]

        earliest_blank = self.earliest_blank_in_word()

        # If there are no blank squares left, override
        # the blank_placement setting
        if blank_placement and \
           not any(self.grid.cells.get(pos).is_blankish for
                   pos in itertools.chain(*self.grid.across_words)):
            blank_placement = False

        # Otherwise, if blank_placement is on, put the
        # cursor in the earliest available blank spot not
        # in the current word
        if blank_placement and earliest_blank:
            self.position = earliest_blank
        elif blank_placement and not earliest_blank:
            self.advance_to_next_word(blank_placement)

    def retreat_to_previous_word(self,
                                 end_placement=False,
                                 blank_placement=False):
        """ move back to previous word """
        if self.direction == "across":
            word_group = self.grid.across_words
            next_words = self.grid.down_words_grouped
        elif self.direction == "down":
            word_group = self.grid.down_words_grouped
            next_words = self.grid.across_words

        word_index = word_group.index(self.current_word())

        pos = -1 if end_placement else 0

        if word_index == 0:
            self.switch_direction()
            self.position = next_words[-1][pos]
        else:
            new_word = word_group[word_index - 1]
            self.position = new_word[pos]

        # If there are no blank squares left, override
        # the blank_placement setting
        if blank_placement and \
           not any(self.grid.cells.get(pos).is_blankish for
                   pos in itertools.chain(*self.grid.across_words)):
            blank_placement = False

        if blank_placement and self.earliest_blank_in_word():
            self.position = self.earliest_blank_in_word()
        elif blank_placement and not self.earliest_blank_in_word():
            self.retreat_to_previous_word(end_placement, blank_placement)

    def earliest_blank_in_word(self):
        """ find the earliest blank in a word """
        blanks = (pos for pos in self.current_word()
                  if self.grid.cells.get(pos).is_blankish)
        return next(blanks, None)

    def move_right(self):
        """ moves right """
        spaces = list(itertools.chain(*self.grid.across_words))
        current_space = spaces.index(self.position)
        ordered_spaces = spaces[current_space + 1:] + spaces[:current_space]

        return next(iter(ordered_spaces))

    def move_left(self):
        """ moves left """
        spaces = list(itertools.chain(*self.grid.across_words))
        current_space = spaces.index(self.position)
        ordered_spaces = (spaces[current_space - 1::-1] +
                          spaces[:current_space:-1])

        return next(iter(ordered_spaces))

    def move_down(self):
        """ moves down """
        spaces = list(itertools.chain(*self.grid.down_words))
        current_space = spaces.index(self.position)
        ordered_spaces = spaces[current_space + 1:] + spaces[:current_space]

        return next(iter(ordered_spaces))

    def move_up(self):
        """ moves up """
        spaces = list(itertools.chain(*self.grid.down_words))
        current_space = spaces.index(self.position)
        ordered_spaces = (spaces[current_space - 1::-1] +
                          spaces[:current_space:-1])

        return next(iter(ordered_spaces))

    def current_word(self):
        """ gets the current word """
        pos = self.position
        word = []

        if self.direction == "across":
            word = next((w for w in self.grid.across_words if pos in w), [])
        if self.direction == "down":
            word = next((w for w in self.grid.down_words if pos in w), [])

        return word

    def go_to_numbered_square(self):
        """ goes to a numbered square """
        num = self.grid.get_notification_input("Enter square number:",
                                               input_condition=str.isdigit)
        if num:
            pos = next((pos for pos in self.grid.cells
                        if self.grid.cells.get(pos).number == int(num)),
                       None)
            if pos:
                self.position = pos
                self.grid.send_notification(
                    "Moved cursor to square {}.".format(num))
            else:
                self.grid.send_notification("Not a valid number.")
        else:
            self.grid.send_notification("No valid number entered.")


class Timer(threading.Thread):
    """ This is our timer """

    def __init__(self, grid, starting_seconds=0, is_running=True, active=True):
        self.starting_seconds = starting_seconds
        self.is_running = is_running
        self.active = active
        self.time_passed = 0
        self.start_time = 0

        super().__init__(daemon=True)

        self.grid = grid

    def run(self):
        """ Without further ado, it's time to start... RUNNING!! """
        self.start_time = time.time()
        self.time_passed = self.starting_seconds

        self.show_time()

        while self.active:
            if self.is_running:
                self.time_passed = (self.starting_seconds
                                    + int(time.time() - self.start_time))
                self.show_time()

            time.sleep(0.5)

    def show_time(self):
        """ show the time on our timer """
        y_coord = 2
        x_coord = self.grid.grid_x + self.grid.column_count * 4 - 7

        print(self.grid.term.move(y_coord, x_coord)
              + self.display_format())

    def display_format(self):
        """ build our time format for display """
        # pylint: disable=invalid-name
        time_amount = self.time_passed

        m, s = divmod(time_amount, 60)
        h, m = divmod(m, 60)

        ch = '{h:02d}:'.format(h=h) if h else '   '
        time_string = '{ch}{m:02d}:{s:02d}'.format(ch=ch, m=m, s=s)

        return time_string

    def save_format(self):
        """ build our time format for saving """
        time_amount = self.time_passed

        save_string = '{t},{r}'.format(t=int(time_amount), r=int(self.active))

        save_bytes = save_string.encode(puz.ENCODING)

        return save_bytes

    def pause(self):
        """ pause our timer """
        self.is_running = False

    def unpause(self):
        """ unpause our timer """
        self.starting_seconds = self.time_passed
        self.start_time = time.time()
        self.is_running = True


class Solver: # pylint: disable=too-few-public-methods
    """ This is our main engine for driving the solving UI """

    def __init__(self):
        version_dir = os.path.abspath(os.path.dirname((__file__)))
        version_file = os.path.join(version_dir, 'version')
        with open(version_file) as file:
            version = file.read().strip()

        parser = argparse.ArgumentParser(
            prog='cursewords',
            description="A terminal-based crossword puzzle solving interface.")

        parser.add_argument('filename', metavar='PUZfile',
                            help="path of AcrossLite .puz puzzle file")
        parser.add_argument('--downs-only', action='store_true',
                            help="""displays only the down clues""")
        parser.add_argument('--debug', action='store_true',
                            help="""run in debugging mode""")
        parser.add_argument('--version', action='version', version=version)

        args = parser.parse_args()
        filename = args.filename
        downs_only = args.downs_only # pylint: disable=unused-variable
        debug = args.debug

        try:
            puzfile = puz.read(filename)
        except:
            if debug:
                raise
            sys.exit("Unable to parse {} as a .puz file.".format(filename))

        term = Terminal()

        grid_x = 2
        grid_y = 4

        grid = Grid(grid_x, grid_y, term) # pylint: disable=undefined-variable
        grid.load(puzfile)

        puzzle_width = 4 * grid.column_count
        puzzle_height = 2 * grid.row_count

        min_width = (puzzle_width
                     + grid_x
                     + 2) # a little breathing room

        min_height = (puzzle_height
                      + grid_y # includes the top bar + timer
                      + 2 # padding above clues
                      + 3 # clue area
                      + 2 # toolbar
                      + 2) # again, just some breathing room

        necessary_resize = []
        if term.width < min_width:
            necessary_resize.append("wider")
        if term.height < min_height:
            necessary_resize.append("taller")

        if necessary_resize:
            exit_text = textwrap.dedent("""\
            This puzzle is {} columns wide and {} rows tall.
            The terminal window must be {} to properly display
            it.""".format(
                grid.column_count, grid.row_count,
                ' and '.join(necessary_resize)))
            sys.exit(' '.join(exit_text.splitlines()))

        if grid.puzfile.has_rebus():
            exit_text = textwrap.dedent("""\
            This puzzle contains features not yet supported
            by cursewords. Sorry about that!""")
            sys.exit(' '.join(exit_text.splitlines()))

        print(term.enter_fullscreen())
        print(term.clear())

        grid.draw()
        grid.number()
        grid.fill()

        software_info = 'cursewords v{}'.format(version)
        puzzle_info = '{grid.title} - {grid.author}'.format(grid=grid)
        padding = 2
        sw_width = len(software_info) + 5
        pz_width = term.width - sw_width - padding
        if len(puzzle_info) > pz_width:
            puzzle_info = "{}…".format(puzzle_info[:pz_width - 1])

        headline = " {:<{pz_w}}{:>{sw_w}} ".format(
            puzzle_info, software_info, pz_w=pz_width, sw_w=sw_width)

        with term.location(x=0, y=0):
            print(term.dim(term.reverse(headline)))

    def solve(self):
        """ our main solving loop """
        toolbar = ''
        commands = [("^Q", "quit"),
                    ("^S", "save"),
                    ("^P", "pause"),
                    ("^C", "check"),
                    ("^R", "reveal"),
                    ("^G", "go to"),
                    ("^X", "clear"),
                    ("^Z", "reset"),]

        if term.width >= 15 * len(commands):
            for shortcut, action in commands:
                shortcut = term.reverse(shortcut)
                toolbar += "{:<25}".format(' '.join([shortcut, action]))

            with term.location(x=grid_x, y=term.height):
                print(toolbar, end='')
        else:
            grid.notification_area = (grid.notification_area[0] - 1, grid_x)
            command_split = int(len(commands)/2) - 1
            for idx, (shortcut, action) in enumerate(commands):
                shortcut = term.reverse(shortcut)
                toolbar += "{:<25}".format(' '.join([shortcut, action]))

                if idx == command_split:
                    toolbar += '\n' + grid_x * ' '

            with term.location(x=grid_x, y=term.height - 2):
                print(toolbar, end='')

        clue_width = min(int(1.3 * (puzzle_width) - grid_x),
                         term.width - 2 - grid_x)

        clue_wrapper = textwrap.TextWrapper(
            width=clue_width, max_lines=3, subsequent_indent=grid_x * ' ')

        start_pos = grid.across_words[0][0]
        cursor = Cursor(start_pos, "across", grid)

        old_word = []
        old_position = start_pos
        keypress = ''
        puzzle_paused = False
        puzzle_complete = False
        modified_since_save = False
        to_quit = False

        timer = Timer(grid, starting_seconds=int(grid.start_time),
                      is_running=True, active=bool(int(grid.timer_active)))
        timer.start()

        info_location = {'x': grid_x, 'y': grid_y + 2 * grid.row_count + 2}

        with term.raw(), term.hidden_cursor():
            while not to_quit:
                # First up we draw all the necessary stuff. If the current word
                # is different from the word the last time through the loop:
                if cursor.current_word() is not old_word:
                    overwrite_mode = False
                    for pos in old_word:
                        grid.draw_cell(pos)
                    for pos in cursor.current_word():
                        grid.draw_highlighted_cell(pos)

                # Draw the clue for the new word:
                    if cursor.direction == "across":
                        num_index = grid.across_words.index(
                            cursor.current_word())
                        clue = grid.across_clues[num_index]
                        if downs_only:
                            clue = "—"
                    elif cursor.direction == "down":
                        num_index = grid.down_words_grouped.index(
                            cursor.current_word())
                        clue = grid.down_clues[num_index]

                    num = str(grid.cells.get(cursor.current_word()[0]).number)
                    compiled_clue = (num + " " + cursor.direction.upper()
                                     + ": " + clue)
                    wrapped_clue = clue_wrapper.wrap(compiled_clue)
                    wrapped_clue += [''] * (3 - len(wrapped_clue))
                    wrapped_clue = [line + term.clear_eol
                                    for line in wrapped_clue]

                    # This is fun: since we're in raw mode, \n isn't
                    # sufficient to return the printing location to the
                    # first column. If you don't also have \r,
                    # it
                    #    prints
                    #           like
                    #                this after each newline
                    print(term.move(info_location['y'], info_location['x'])
                          + '\r\n'.join(wrapped_clue))

                # Otherwise, just draw the old square now that it's not under
                # the cursor
                else:
                    grid.draw_highlighted_cell(old_position)

                current_cell = grid.cells.get(cursor.position)
                grid.draw_cursor_cell(cursor.position)

                # Check if the puzzle is complete!
                if not puzzle_complete and all(grid.cells.get(pos).is_correct
                                               for pos in grid.cells):
                    puzzle_complete = True
                    with term.location(x=grid_x, y=2):
                        print(term.reverse("You've completed the puzzle!"),
                              term.clear_eol)
                    timer.show_time()
                    timer.active = False

                blank_cells_remaining = any(grid.cells.get(pos).is_blankish
                                            for pos in grid.cells)

                # Where the magic happens: get key input
                keypress = term.inkey()

                old_position = cursor.position
                old_word = cursor.current_word()

                # ctrl-q
                if keypress == chr(17):
                    to_quit = grid.confirm_quit(modified_since_save)
                    if not to_quit:
                        grid.send_notification("Quit command canceled.")

                # ctrl-s
                elif keypress == chr(19):
                    grid.puzfile.extensions[puz.Extensions.Timer] = timer.save_format()
                    grid.save(filename)
                    modified_since_save = False

                # ctrl-p
                elif keypress == chr(16) and not puzzle_complete:
                    if timer.is_running:
                        timer.pause()
                        grid.draw()

                        with term.location(**info_location):
                            print('\r\n'.join(['PUZZLE PAUSED' + term.clear_eol,
                                               term.clear_eol,
                                               term.clear_eol]))

                        puzzle_paused = True

                    else:
                        timer.unpause()
                        grid.fill()
                        old_word = []

                        puzzle_paused = False

                # ctrl-z
                elif keypress == chr(26):
                    confirm = grid.confirm_reset()
                    if confirm:
                        grid.send_notification("Puzzle reset.")
                        for pos in grid.cells:
                            cell = grid.cells.get(pos)
                            if cell.is_letter:
                                cell.clear()
                                cell.set_corrected(False)
                                cell.set_revealed(False)
                                grid.draw_cell(pos)
                        timer.starting_seconds = timer.time_passed = 0
                        timer.start_time = time.time()
                        timer.show_time()
                        modified_since_save = True
                        if not puzzle_paused:
                            old_word = []
                    else:
                        grid.send_notification("Reset command canceled.")

                # If the puzzle is paused, skip all the rest of the logic
                elif puzzle_paused:
                    continue

                # ctrl-c
                elif keypress == chr(3):
                    group = grid.get_notification_input(
                        "Check (l)etter, (w)ord, or (p)uzzle?", limit=1)
                    scope = ''
                    if group.lower() == 'l':
                        scope = 'letter'
                        grid.check_cell(cursor.position)
                    elif group.lower() == 'w':
                        scope = 'word'
                        grid.check_cells(cursor.current_word())
                    elif group.lower() == 'p':
                        scope = 'puzzle'
                        grid.check_cells(grid.cells)

                    if scope:
                        grid.send_notification("Checked {scope} for errors.".
                                               format(scope=scope))
                    else:
                        grid.send_notification("No valid input entered.")

                    old_word = []

                # ctrl-g
                elif keypress == chr(7):
                    cursor.go_to_numbered_square()

                # ctrl-x
                elif keypress == chr(24):
                    confirm = grid.confirm_clear()
                    if confirm:
                        grid.send_notification("Puzzle cleared.")
                        for pos in grid.cells:
                            cell = grid.cells.get(pos)
                            if cell.is_letter:
                                cell.clear()
                                grid.draw_cell(pos)
                        old_word = []
                        modified_since_save = True
                    else:
                        grid.send_notification("Clear command canceled.")


                # ctrl-r
                elif keypress == chr(18):
                    group = grid.get_notification_input(
                        "Reveal (l)etter, (w)ord, or (p)uzzle?", limit=1)
                    scope = ''
                    if group.lower() == 'l':
                        scope = 'letter'
                        grid.reveal_cell(cursor.position)
                    elif group.lower() == 'w':
                        scope = 'word'
                        grid.reveal_cells(cursor.current_word())
                    elif group.lower() == 'p':
                        scope = 'puzzle'
                        grid.reveal_cells(grid.cells)

                    if scope:
                        grid.send_notification("Revealed answers for {scope}.".
                                               format(scope=scope))
                    else:
                        grid.send_notification("No valid input entered.")

                    old_word = []

                # Letter entry
                elif not puzzle_complete and keypress.isalnum():
                    if not current_cell.is_blankish:
                        overwrite_mode = True
                    current_cell.entry = keypress.upper()

                    if current_cell.is_marked_wrong:
                        current_cell.set_marked_wrong(False)
                        current_cell.set_corrected(True)
                    modified_since_save = True
                    cursor.advance_within_word(overwrite_mode, wrap_mode=True)

                # Delete key
                elif not puzzle_complete and keypress.name == 'KEY_DELETE':
                    current_cell.clear()
                    overwrite_mode = True
                    modified_since_save = True
                    cursor.retreat_within_word(end_placement=True)

                # Navigation
                elif keypress.name in ['KEY_TAB'] and current_cell.is_blankish:
                    cursor.advance_to_next_word(blank_placement=True)

                elif keypress.name in ['KEY_TAB'] and not current_cell.is_blankish:
                    cursor.advance_within_word(overwrite_mode=False)

                elif keypress.name in ['KEY_PGDOWN']:
                    cursor.advance_to_next_word()

                elif keypress.name in ['KEY_BTAB']:
                    cursor.retreat_within_word(blank_placement=True)

                elif keypress.name in ['KEY_PGUP']:
                    cursor.retreat_to_previous_word()

                elif (keypress.name == 'KEY_ENTER' or keypress == ' ' or
                      (cursor.direction == "across" and
                       keypress.name in ['KEY_DOWN', 'KEY_UP']) or
                      (cursor.direction == "down" and
                       keypress.name in ['KEY_LEFT', 'KEY_RIGHT'])):

                    cursor.switch_direction()
                    if not cursor.current_word():
                        cursor.switch_direction()

                elif ((cursor.direction == "across" and
                       keypress.name == 'KEY_RIGHT') or
                      (cursor.direction == "down" and
                       keypress.name == 'KEY_DOWN')):

                    cursor.advance()

                elif ((cursor.direction == "across" and
                       keypress.name == 'KEY_LEFT') or
                      (cursor.direction == "down" and
                       keypress.name == 'KEY_UP')):

                    cursor.retreat()

                elif keypress in ['}', ']']:
                    cursor.advance_perpendicular()
                    if (keypress == '}' and blank_cells_remaining):
                        while not grid.cells.get(cursor.position).is_blankish:
                            cursor.advance_perpendicular()

                elif keypress in ['{', '[']:
                    cursor.retreat_perpendicular()
                    if (keypress == '{' and blank_cells_remaining):
                        while not grid.cells.get(cursor.position).is_blankish:
                            cursor.retreat_perpendicular()

        print(term.exit_fullscreen())


# -*- coding: utf-8 -*-
# vim:fenc=utf-8:tw=75
