#! /usr/bin/env python3

"""
Control flow for solving mode
"""

# pylint: disable=too-many-arguments
# pylint: disable=too-many-branches
# pylint: disable=too-many-boolean-expressions
# pylint: disable=too-many-locals
# pylint: disable=too-many-public-methods
# pylint: disable=too-many-statements

import itertools
import sys
import textwrap
import threading
import time
import puz

from blessed import Terminal

from . import chars
from .grid import Grid


class Cursor:
    """ This class represents our cursor and active region """

    def __init__(self, position, direction, solver, grid):
        self.position = position
        self.direction = direction
        self.solver = solver
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
        num = self.solver.get_notification_input("Enter square number:",
                                                 input_condition=str.isdigit)
        if num:
            pos = next((pos for pos in self.grid.cells
                        if self.grid.cells.get(pos).number == int(num)),
                       None)
            if pos:
                self.position = pos
                self.solver.send_notification(
                    "Moved cursor to square {}.".format(num))
            else:
                self.solver.send_notification("Not a valid number.")
        else:
            self.solver.send_notification("No valid number entered.")


class Timer(threading.Thread):
    """ This is our timer """

    def __init__(self, grid, term, starting_seconds=0, is_running=True, active=True):
        self.starting_seconds = starting_seconds
        self.is_running = is_running
        self.active = active
        self.time_passed = 0
        self.start_time = 0

        super().__init__(daemon=True)

        self.grid = grid
        self.term = term

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
        x_coord = self.grid.x + self.grid.column_count * 4 - 7

        print(self.term.move(y_coord, x_coord)
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


class Solver:
    """ This is our main engine for driving the solving UI """

    def __init__(self, filename, version, downs_only=False, debug=False):
        self.filename = filename
        try:
            puzfile = puz.read(filename)
        except: # pylint: disable=bare-except
            if debug:
                raise
            sys.exit("Unable to parse {} as a .puz file.".format(
                self.filename))

        self.downs_only = downs_only

        self.grid = Grid(2, 4)
        self.grid.load(puzfile)

        self.start_time = 0
        self.timer_active = 0
        self.term = Terminal()
        self.notification_area = (self.term.height-2, self.grid.x)

        necessary_resize = []
        if self.term.width < self.min_width:
            necessary_resize.append("wider")
        if self.term.height < self.min_height:
            necessary_resize.append("taller")

        if necessary_resize:
            exit_text = textwrap.dedent("""\
            This puzzle is {} columns wide and {} rows tall.
            The terminal window must be {} to properly display
            it.""".format(
                self.grid.column_count, self.grid.row_count,
                ' and '.join(necessary_resize)))
            sys.exit(' '.join(exit_text.splitlines()))

        if self.puzfile.has_rebus():
            exit_text = textwrap.dedent("""\
            This puzzle contains features not yet supported
            by cursewords. Sorry about that!""")
            sys.exit(' '.join(exit_text.splitlines()))

        print(self.term.enter_fullscreen())
        print(self.term.clear())

        self.draw()
        self.grid.number()
        self.fill()

        software_info = 'cursewords v{}'.format(version)
        puzzle_info = '{grid.title} - {grid.author}'.format(grid=self.grid)
        padding = 2
        sw_width = len(software_info) + 5
        pz_width = self.term.width - sw_width - padding
        if len(puzzle_info) > pz_width:
            puzzle_info = "{}…".format(puzzle_info[:pz_width - 1])

        headline = " {:<{pz_w}}{:>{sw_w}} ".format(
            puzzle_info, software_info, pz_w=pz_width, sw_w=sw_width)

        with self.term.location(x=0, y=0):
            print(self.term.dim(self.term.reverse(headline)))

    @property
    def cells(self):
        """ proxy self.grid.cells just to keep from having to type
        self.grid.cells everywhere
        """

        return self.grid.cells

    @property
    def min_width(self):
        """ The minimum terminal width we can work with """
        return (self.puzzle_width
                + self.grid.x
                + 2) # a little breathing room

    @property
    def min_height(self):
        """ The minimum terminal height we can work with """
        return (self.puzzle_height
                + self.grid.y # includes the top bar + timer
                + 2 # padding above clues
                + 3 # clue area
                + 2 # toolbar
                + 2) # again, just some breathing room

    @property
    def puzfile(self):
        """ our puz file """
        return self.grid.puzfile

    @property
    def puzzle_width(self):
        """ The width of our grid, in screen characters """
        return 4 * self.grid.column_count

    @property
    def puzzle_height(self):
        """ The height of our grid, in screen characters """
        return 2 * self.grid.row_count

    def _make_timer(self):
        """ get our timer start time and state from the puzfile """

        timer_bytes = \
            self.grid.puzfile.extensions.get(puz.Extensions.Timer, None)
        if timer_bytes:
            start_time, active = timer_bytes.decode().split(',')
            start_time = int(start_time)
            active = bool(int(active))
        else:
            start_time = 0
            active = True

        return Timer(self.grid, self.term, starting_seconds=start_time,
                     is_running=True, active=active)
    def draw(self):
        """ draw our grid """
        top_row = self.grid.get_top_row()
        bottom_row = self.grid.get_bottom_row()
        middle_row = self.grid.get_middle_row()
        divider_row = self.grid.get_divider_row()

        print(self.term.move(self.grid.y, self.grid.x)
              + self.term.dim(top_row))
        for index, y_val in enumerate(
                range(self.grid.y + 1,
                      self.grid.y + self.grid.row_count * 2), 1):
            if index % 2 == 0:
                print(self.term.move(y_val, self.grid.x) +
                      self.term.dim(divider_row))
            else:
                print(self.term.move(y_val, self.grid.x) +
                      self.term.dim(middle_row))
        print(self.term.move(self.grid.y + self.grid.row_count * 2,
                             self.grid.x)
              + self.term.dim(bottom_row))

    def fill(self):
        """ fill the grid with its solution """

        for position in self.cells:
            y_coord, x_coord = self.to_term(position)
            cell = self.cells[position]
            if cell.is_letter:
                self.draw_cell(position)
            elif cell.is_block:
                print(self.term.move(y_coord, x_coord - 1) +
                      self.term.dim(chars.squareblock))

            if cell.number:
                small = chars.small_nums(cell.number)
                x_pos = x_coord - 1
                print(self.term.move(y_coord - 1, x_pos) + small)

    def confirm_quit(self, modified_since_save):
        """ confirm that the user is done cursing at this puzzle """

        confirmed = True
        if modified_since_save:
            confirmation = self.get_notification_input(
                "Quit without saving? (y/n)",
                limit=1, blocking=True, timeout=5)
            confirmed = bool(confirmation.lower() == 'y')

        return confirmed

    def confirm_clear(self):
        """ confirm that the user wants to curse at the blank puzzle again """

        confirmation = self.get_notification_input(
            "Clear puzzle? (y/n)", limit=1, blocking=True, timeout=5)
        confirmed = bool(confirmation.lower() == 'y')
        return confirmed

    def confirm_reset(self):
        """ confirm that the user wants to reset this cursed puzzle """

        confirmation = self.get_notification_input(
            "Reset puzzle? (y/n)", limit=1, blocking=True, timeout=5)
        confirmed = bool(confirmation.lower() == 'y')
        return confirmed

    def reveal_cell(self, pos):
        """ reveal one cursed cell """

        cell = self.cells.get(pos)
        if cell.is_blankish or not cell.is_correct:
            cell.entry = cell.solution
            cell.set_revealed(True)
            self.draw_cell(pos)

    def reveal_cells(self, pos_list):
        """ reveal a bunch of cursed cells """

        for pos in pos_list:
            self.reveal_cell(pos)

    def check_cell(self, pos):
        """ check one cursed cell """

        cell = self.cells.get(pos)
        if not cell.is_blank and not cell.is_correct:
            cell.set_marked_wrong(True)
            self.draw_cell(pos)

    def check_cells(self, pos_list):
        """ chuck a bunch of cursed cells """

        for pos in pos_list:
            self.check_cell(pos)

    def to_term(self, position):
        """ convert one cursed cell position from grid to terminal coordinates
        """

        point_x, point_y = position
        term_x = self.grid.x + (4 * point_x) + 2
        term_y = self.grid.y + (2 * point_y) + 1
        return (term_y, term_x)

    def compile_cell(self, position):
        """ compile the various attributes of one cell """

        cell = self.cells.get(position)
        if cell.is_blank:
            value = " "
        else:
            value = cell.entry

        if cell.is_circled:
            value = chars.encircle(value)

        if cell.is_marked_wrong:
            value = self.term.red(value.lower())
        else:
            value = self.term.bold(value)

        markup = ' '

        if cell.is_corrected:
            markup = self.term.red(".")
        if cell.is_revealed:
            markup = self.term.red(":")

        return value, markup

    def draw_cell(self, position):
        """ draw a cell on the terminal """

        value, markup = self.compile_cell(position)
        value += markup
        print(self.term.move(*self.to_term(position)) + value)

    def draw_highlighted_cell(self, position):
        """ draw a highlit cell on the terminal """

        value, markup = self.compile_cell(position)
        value = self.term.underline(value) + markup
        print(self.term.move(*self.to_term(position)) + value)

    def draw_cursor_cell(self, position):
        """ draw a cursor on the terminal """

        value, markup = self.compile_cell(position)
        value = self.term.reverse(value) + markup
        print(self.term.move(*self.to_term(position)) + value)

    def get_notification_input(self, message, timeout=5, limit=3,
                               input_condition=str.isalnum, blocking=False):
        """ get input from our notification system """

        # If there's already a notification timer running, stop it.
        try:
            self.grid.notification_timer.cancel()
        except: # pylint: disable=bare-except
            pass

        input_phrase = message + " "
        key_input_place = len(input_phrase)
        print(self.term.move(*self.notification_area)
              + self.term.reverse(input_phrase)
              + self.term.clear_eol)

        user_input = ''
        keypress = None
        while keypress != '' and len(user_input) < limit:
            keypress = self.term.inkey(timeout)
            if input_condition(keypress):
                user_input += keypress
                print(self.term.move(self.notification_area[0],
                                     self.notification_area[1]
                                     + key_input_place),
                      user_input)
            elif keypress.name in ['KEY_DELETE']:
                user_input = user_input[:-1]
                print(self.term.move(self.notification_area[0],
                                     self.notification_area[1]
                                     + key_input_place),
                      user_input + self.term.clear_eol)
            elif blocking and keypress.name not in ['KEY_ENTER', 'KEY_ESCAPE']:
                continue
            else:
                break

        return user_input

    def send_notification(self, message, timeout=5):
        """ send a notification """

        self.grid.notification_timer = \
            threading.Timer(timeout, self.clear_notification_area)
        self.grid.notification_timer.daemon = True
        print(self.term.move(*self.notification_area)
              + self.term.reverse(message) + self.term.clear_eol)
        self.grid.notification_timer.start()

    def clear_notification_area(self):
        """ clear our notification """

        print(self.term.move(*self.notification_area) + self.term.clear_eol)

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

        if self.term.width >= 15 * len(commands):
            for shortcut, action in commands:
                shortcut = self.term.reverse(shortcut)
                toolbar += "{:<25}".format(' '.join([shortcut, action]))

            with self.term.location(x=self.grid.x, y=self.term.height):
                print(toolbar, end='')
        else:
            self.grid.notification_area = (self.grid.notification_area[0] - 1,
                                           self.grid.x)
            command_split = int(len(commands)/2) - 1
            for idx, (shortcut, action) in enumerate(commands):
                shortcut = self.term.reverse(shortcut)
                toolbar += "{:<25}".format(' '.join([shortcut, action]))

                if idx == command_split:
                    toolbar += '\n' + self.grid.x * ' '

            with self.term.location(x=self.grid.x, y=self.term.height - 2):
                print(toolbar, end='')

        clue_width = min(int(1.3 * (self.puzzle_width) - self.grid.x),
                         self.term.width - 2 - self.grid.x)

        clue_wrapper = textwrap.TextWrapper(
            width=clue_width, max_lines=3, subsequent_indent=self.grid.x * ' ')

        start_pos = self.grid.across_words[0][0]
        cursor = Cursor(start_pos, "across", self, self.grid)

        old_word = []
        old_position = start_pos
        keypress = ''
        puzzle_paused = False
        puzzle_complete = False
        modified_since_save = False
        to_quit = False

        timer = self._make_timer()
        timer.start()

        info_location = {'x': self.grid.x,
                         'y': self.grid.y + 2 * self.grid.row_count + 2}

        with self.term.raw(), self.term.hidden_cursor():
            while not to_quit:
                # First up we draw all the necessary stuff. If the current word
                # is different from the word the last time through the loop:
                if cursor.current_word() is not old_word:
                    overwrite_mode = False
                    for pos in old_word:
                        self.draw_cell(pos)
                    for pos in cursor.current_word():
                        self.draw_highlighted_cell(pos)

                # Draw the clue for the new word:
                    if cursor.direction == "across":
                        num_index = self.grid.across_words.index(
                            cursor.current_word())
                        clue = self.grid.across_clues[num_index]
                        if self.downs_only:
                            clue = "—"
                    elif cursor.direction == "down":
                        num_index = self.grid.down_words_grouped.index(
                            cursor.current_word())
                        clue = self.grid.down_clues[num_index]

                    num = self.cells.get(cursor.current_word()[0]).number
                    num = str(num)
                    compiled_clue = (num + " " + cursor.direction.upper()
                                     + ": " + clue)
                    wrapped_clue = clue_wrapper.wrap(compiled_clue)
                    wrapped_clue += [''] * (3 - len(wrapped_clue))
                    wrapped_clue = [line + self.term.clear_eol
                                    for line in wrapped_clue]

                    # This is fun: since we're in raw mode, \n isn't
                    # sufficient to return the printing location to the
                    # first column. If you don't also have \r,
                    # it
                    #    prints
                    #           like
                    #                this after each newline
                    print(self.term.move(info_location['y'], info_location['x'])
                          + '\r\n'.join(wrapped_clue))

                # Otherwise, just draw the old square now that it's not under
                # the cursor
                else:
                    self.draw_highlighted_cell(old_position)

                current_cell = self.cells.get(cursor.position)
                self.draw_cursor_cell(cursor.position)

                # Check if the puzzle is complete!
                if not puzzle_complete and \
                        all(self.cells.get(pos).is_correct
                                for pos in self.cells):
                    puzzle_complete = True
                    with self.term.location(x=self.grid.x, y=2):
                        print(self.term.reverse("You've completed the puzzle!"),
                              self.term.clear_eol)
                    timer.show_time()
                    timer.active = False

                blank_cells_remaining = any(self.cells.get(pos).is_blankish
                                            for pos in self.cells)

                # Where the magic happens: get key input
                keypress = self.term.inkey()

                old_position = cursor.position
                old_word = cursor.current_word()

                # ctrl-q
                if keypress == chr(17):
                    to_quit = self.confirm_quit(modified_since_save)
                    if not to_quit:
                        self.send_notification("Quit command canceled.")

                # ctrl-s
                elif keypress == chr(19):
                    self.puzfile.extensions[puz.Extensions.Timer] = \
                            timer.save_format()
                    self.grid.save(self.filename)
                    modified_since_save = False

                # ctrl-p
                elif keypress == chr(16) and not puzzle_complete:
                    if timer.is_running:
                        timer.pause()
                        self.draw()

                        with self.term.location(**info_location):
                            print('\r\n'.join([
                                'PUZZLE PAUSED' + self.term.clear_eol,
                                self.term.clear_eol,
                                self.term.clear_eol]))

                        puzzle_paused = True

                    else:
                        timer.unpause()
                        self.fill()
                        old_word = []

                        puzzle_paused = False

                # ctrl-z
                elif keypress == chr(26):
                    confirm = self.confirm_reset()
                    if confirm:
                        self.send_notification("Puzzle reset.")
                        for pos in self.cells:
                            cell = self.cells.get(pos)
                            if cell.is_letter:
                                cell.clear()
                                cell.set_corrected(False)
                                cell.set_revealed(False)
                                self.draw_cell(pos)
                        timer.starting_seconds = timer.time_passed = 0
                        timer.start_time = time.time()
                        timer.show_time()
                        modified_since_save = True
                        puzzle_complete = False
                        with self.term.location(x=self.grid.x, y=2):
                            print("                            ",
                                  self.term.clear_eol)
                        if puzzle_paused:
                            puzzle_paused = False
                            timer.unpause()
                        else:
                            old_word = []
                    else:
                        self.send_notification("Reset command canceled.")

                # If the puzzle is paused, skip all the rest of the logic
                elif puzzle_paused:
                    continue

                # ctrl-c
                elif keypress == chr(3):
                    group = self.get_notification_input(
                        "Check (l)etter, (w)ord, or (p)uzzle?", limit=1)
                    scope = ''
                    if group.lower() == 'l':
                        scope = 'letter'
                        self.check_cell(cursor.position)
                    elif group.lower() == 'w':
                        scope = 'word'
                        self.check_cells(cursor.current_word())
                    elif group.lower() == 'p':
                        scope = 'puzzle'
                        self.check_cells(self.cells)

                    if scope:
                        self.send_notification(
                            "Checked {scope} for errors.".format(scope=scope))
                    else:
                        self.send_notification("No valid input entered.")

                    old_word = []

                # ctrl-g
                elif keypress == chr(7):
                    cursor.go_to_numbered_square()

                # ctrl-x
                elif keypress == chr(24):
                    confirm = self.confirm_clear()
                    if confirm:
                        self.send_notification("Puzzle cleared.")
                        for pos in self.cells:
                            cell = self.cells.get(pos)
                            if cell.is_letter:
                                cell.clear()
                                self.draw_cell(pos)
                        old_word = []
                        modified_since_save = True
                    else:
                        self.send_notification("Clear command canceled.")

                # ctrl-r
                elif keypress == chr(18):
                    group = self.get_notification_input(
                        "Reveal (l)etter, (w)ord, or (p)uzzle?", limit=1)
                    scope = ''
                    if group.lower() == 'l':
                        scope = 'letter'
                        self.reveal_cell(cursor.position)
                    elif group.lower() == 'w':
                        scope = 'word'
                        self.reveal_cells(cursor.current_word())
                    elif group.lower() == 'p':
                        scope = 'puzzle'
                        self.reveal_cells(self.cells)

                    if scope:
                        self.send_notification(
                            "Revealed answers for {scope}.".format(scope=scope))
                    else:
                        self.send_notification("No valid input entered.")

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
                        while not self.cells.get(cursor.position).is_blankish:
                            cursor.advance_perpendicular()

                elif keypress in ['{', '[']:
                    cursor.retreat_perpendicular()
                    if (keypress == '{' and blank_cells_remaining):
                        while not self.cells.get(cursor.position).is_blankish:
                            cursor.retreat_perpendicular()

        print(self.term.exit_fullscreen())


# -*- coding: utf-8 -*-
# vim:fenc=utf-8:tw=75
