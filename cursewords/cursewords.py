# pylint: disable=invalid-name
# pylint: disable=missing-docstring
# pylint: disable=too-many-lines
# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-branches
# pylint: disable=too-many-statements
# pylint: disable=too-many-arguments
# pylint: disable=too-many-boolean-expressions
# pylint: disable=too-many-locals
# pylint: disable=too-many-public-methods
# pylint: disable=bare-except

#! /usr/bin/env python3

import argparse
import functools
import os
import sys
import time
import textwrap
import threading

from blessed import Terminal

from . import characters
from . import puz
from .printer import printer_output

echo = functools.partial(print, end='', flush=True)

class Cell:
    def __init__(self, solution, entry=None):
        self.solution = solution
        self.number = None
        self.entry = entry or "-"
        self.marked_wrong = False
        self.corrected = False
        self.revealed = False
        self.circled = False

    def __str__(self):
        return self.entry

    def clear(self):
        self.entry = "-"
        if self.marked_wrong:
            self.marked_wrong = False
            self.corrected = True

    @property
    def is_block(self):
        return self.solution == "."

    @property
    def is_letter(self):
        return self.solution.isalnum()

    @property
    def is_blank(self):
        return self.entry == "-"

    @property
    def is_blankish(self):
        return self.is_blank or self.marked_wrong

    @property
    def is_correct(self):
        return self.entry == self.solution or self.is_block


class Grid:
    def __init__(self, grid_x, grid_y, term):
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.term = term

        self.puzfile = None
        self.cells = {}
        self.row_count = 0
        self.column_count = 0

        self.title = ''
        self.author = ''

        self.words = dict()
        self.clues = dict()
        self.spaces = dict()

        self.start_time = 0
        self.timer_active = False
        self.notification_timer = None

        self.notification_area = (term.height-2, self.grid_x)

    def load(self, puzfile):
        self.puzfile = puzfile
        self.cells = {}
        self.row_count = puzfile.height
        self.column_count = puzfile.width

        self.title = puzfile.title
        self.author = puzfile.author.strip()

        for i in range(self.row_count):
            for j in range(self.column_count):
                idx = i * self.column_count + j
                entry = self.puzfile.fill[idx]
                self.cells[(j, i)] = Cell(self.puzfile.solution[idx], entry)

        self.words['across'] = []
        for i in range(self.row_count):
            current_word = []
            for j in range(self.column_count):
                if self.cells[(j, i)].is_letter:
                    current_word.append((j, i))
                elif len(current_word) > 1:
                    self.words['across'].append(current_word)
                    current_word = []
                elif current_word:
                    current_word = []
            if len(current_word) > 1:
                self.words['across'].append(current_word)

        self.words['down'] = []
        for j in range(self.column_count):
            current_word = []
            for i in range(self.row_count):
                if self.cells[(j, i)].is_letter:
                    current_word.append((j, i))
                elif len(current_word) > 1:
                    self.words['down'].append(current_word)
                    current_word = []
                elif current_word:
                    current_word = []
            if len(current_word) > 1:
                self.words['down'].append(current_word)

        self.words['down'].sort(key=lambda word: (word[0][1], word[0][0]))

        self.number()

        num = self.puzfile.clue_numbering()
        self.clues['across'] = num.across
        self.clues['down'] = num.down

        self.spaces['across'] = [(j, i) for i in range(self.row_count)
                                 for j in range(self.column_count)
                                 if self.cells[(j, i)].is_letter]
        self.spaces['down'] = [(j, i) for j in range(self.column_count)
                               for i in range(self.row_count)
                               if self.cells[(j, i)].is_letter]


        if self.puzfile.has_markup():
            markup = self.puzfile.markup().markup

            for md, pos in zip(markup, self.cells):
                cell = self.cells.get(pos)
                if md >= 128:
                    cell.circled = True
                    md -= 128
                if md >= 64:
                    cell.revealed = True
                    md -= 64
                if md >= 32:
                    cell.marked_wrong = True
                    md -= 32
                if md == 16:
                    cell.corrected = True

        timer_bytes = self.puzfile.extensions.get(puz.Extensions.Timer, None)
        if timer_bytes:
            self.start_time, self.timer_active = timer_bytes.decode().split(',')
        else:
            self.start_time, self.timer_active = 0, 1

    def render_grid(self, empty=False, blank=False, solution=False):
        grid_rows = []
        for i in range(self.row_count):
            rows = [self.term.dim, self.term.dim]
            for j in range(self.column_count):
                pos = (j, i)
                cell = self.cells.get(pos)
                if i == 0 and j == 0:
                    rows[0] += characters.ulcorner
                elif j == 0:
                    rows[0] += characters.ltee
                elif i == 0:
                    rows[0] += characters.ttee
                else:
                    rows[0] += characters.bigplus

                rows[1] += characters.vline

                if cell.number and not empty:
                    small = str(cell.number).translate(characters.small_nums)
                else:
                    small = ''

                # This is the right way to do it but as long as I'm doing
                # the weird term.dim dance I have to write it a little uglier
                # rows[0] += f'{small:{characters.hline}<3.3}'
                rows[0] += (self.term.normal +
                            small +
                            self.term.dim +
                            characters.hline * (3 - len(small)))

                if empty:
                    rows[1] += '   '
                elif cell.is_block:
                    rows[1] += characters.squareblock
                elif blank:
                    rows[1] += '   '
                elif solution:
                    rows[1] += ' '.join([self.term.normal, self.cells[pos].solution,
                                         self.term.dim])
                else:
                    value, markup = self.compile_cell(pos)
                    value += markup
                    rows[1] += self.term.normal + ' ' + value + self.term.dim

                if j == self.column_count - 1:
                    if i == 0:
                        rows[0] += characters.urcorner
                    else:
                        rows[0] += characters.rtee
                    rows[1] += characters.vline + self.term.normal
                    rows[0] += self.term.normal
            grid_rows.extend(rows)

        bottom_row = self.term.dim + characters.llcorner
        for col in range(1, self.column_count * 4):
            bottom_row += characters.btee if col % 4 == 0 else characters.hline
        bottom_row += characters.lrcorner + self.term.normal

        grid_rows.append(bottom_row)

        return grid_rows

    def draw(self, empty=False):
        grid_rows = self.render_grid(empty=empty)
        for index, row in enumerate(grid_rows):
            echo(self.term.move(self.grid_y + index, self.grid_x) + row)

    def number(self):
        numbered_squares = []
        for word in self.words['across'] + self.words['down']:
            if word[0] not in numbered_squares:
                numbered_squares.append(word[0])

        numbered_squares.sort(key=lambda x: (x[1], x[0]))

        for number, square in enumerate(numbered_squares, 1):
            self.cells.get(square).number = number

    @property
    def blank_cells_remaining(self):
        return any(self.cells.get(pos).is_blankish for pos in self.cells)

    def confirm_quit(self, modified_since_save):
        if modified_since_save:
            confirmation = self.get_notification_input(
                                "Quit without saving? (y/n)",
                                char_limit=1, blocking=True, timeout=5)
            return confirmation.lower() == 'y'
        return True

    def confirm_clear(self):
        confirmation = self.get_notification_input("Clear puzzle? (y/n)",
                                                   char_limit=1,
                                                   blocking=True,
                                                   timeout=5)
        return confirmation.lower() == 'y'

    def confirm_reset(self):
        confirmation = self.get_notification_input("Reset puzzle? (y/n)",
                                                   char_limit=1,
                                                   blocking=True,
                                                   timeout=5)
        return confirmation.lower() == 'y'

    def save(self, filename):
        fill = ''
        for pos in self.cells:
            cell = self.cells[pos]
            if cell.is_block:
                entry = "."
            elif cell.is_blank:
                entry = "-"
            else:
                entry = cell.entry
            fill += entry
        self.puzfile.fill = fill

        if (any(self.cells.get(pos).marked_wrong or
                self.cells.get(pos).corrected
                for pos in self.cells) or
                self.puzfile.has_markup()):
            md = []
            for pos in self.cells:
                cell = self.cells[pos]
                cell_md = 0
                if cell.corrected:
                    cell_md += 16
                if cell.marked_wrong:
                    cell_md += 32
                if cell.revealed:
                    cell_md += 64
                if cell.circled:
                    cell_md += 128
                md.append(cell_md)
            self.puzfile.markup().markup = md

        self.puzfile.save(filename)
        self.send_notification("Current puzzle state saved.")

    def reveal_cell(self, pos):
        cell = self.cells.get(pos)
        if cell.is_blankish or not cell.is_correct:
            cell.entry = cell.solution
            cell.revealed = True
            self.draw_cell(pos)

    def reveal_cells(self, pos_list):
        for pos in pos_list:
            self.reveal_cell(pos)

    def check_cell(self, pos):
        cell = self.cells.get(pos)
        if not cell.is_blank and not cell.is_correct:
            cell.marked_wrong = True
            self.draw_cell(pos)

    def check_cells(self, pos_list):
        for pos in pos_list:
            self.check_cell(pos)

    def to_term(self, position):
        point_x, point_y = position
        term_x = self.grid_x + (4 * point_x) + 2
        term_y = self.grid_y + (2 * point_y) + 1
        return (term_y, term_x)

    def compile_cell(self, position):
        cell = self.cells.get(position)
        value = " " if cell.is_blank else cell.entry

        if cell.circled:
            value = value.translate(characters.encircle)

        if cell.marked_wrong and not cell.revealed:
            value = self.term.red(value.lower())
        else:
            value = self.term.bold(value)

        markup = ' '

        if cell.corrected:
            markup = self.term.red(".")
        if cell.revealed:
            markup = self.term.red(":")

        return value, markup

    def draw_cell(self, position):
        value, markup = self.compile_cell(position)
        value += markup
        echo(self.term.move(*self.to_term(position)) + value)

    def draw_highlighted_cell(self, position):
        value, markup = self.compile_cell(position)
        value = self.term.underline(value) + markup
        echo(self.term.move(*self.to_term(position)) + value)

    def draw_cursor_cell(self, position):
        value, markup = self.compile_cell(position)
        value = self.term.reverse(value) + markup
        echo(self.term.move(*self.to_term(position)) + value)

    def get_notification_input(self, message, timeout=5, char_limit=3,
                               input_condition=str.isalnum, blocking=False):

        # If there's already a notification timer running, stop it.
        try:
            self.notification_timer.cancel()
        except:
            pass

        input_phrase = message + " "
        key_input_place = len(input_phrase)
        echo(self.term.move(*self.notification_area) +
             self.term.reverse(input_phrase) +
             self.term.clear_eol)

        user_input = ''
        keypress = None
        while keypress != '' and len(user_input) < char_limit:
            keypress = self.term.inkey(timeout)
            if input_condition(keypress):
                user_input += keypress
                echo(self.term.move(self.notification_area[0],
                                    self.notification_area[1] +
                                    key_input_place),
                     user_input)
            elif keypress.name in ['KEY_DELETE', 'KEY_BACKSPACE']:
                user_input = user_input[:-1]
                echo(self.term.move(self.notification_area[0],
                                    self.notification_area[1] +
                                    key_input_place),
                     user_input + self.term.clear_eol)
            elif blocking and keypress.name not in ['KEY_ENTER', 'KEY_ESCAPE']:
                continue
            else:
                break

        return user_input

    def send_notification(self, message, timeout=5):
        self.notification_timer = threading.Timer(timeout,
                                                  self.clear_notification_area)
        self.notification_timer.daemon = True
        echo(self.term.move(*self.notification_area) +
             self.term.reverse(message) + self.term.clear_eol)
        self.notification_timer.start()

    def clear_notification_area(self):
        echo(self.term.move(*self.notification_area) + self.term.clear_eol)


class Cursor:
    def __init__(self, position, direction, grid):
        self.position = position
        self.direction = direction
        self.grid = grid

    def switch_direction(self, to=None):
        if to:
            self.direction = to
        elif self.direction == "across":
            self.direction = "down"
        elif self.direction == "down":
            self.direction = "across"

    def advance(self):
        if self.direction == "across":
            self.position = self.move_right()
        elif self.direction == "down":
            self.position = self.move_down()

    def retreat(self):
        if self.direction == "across":
            self.position = self.move_left()
        elif self.direction == "down":
            self.position = self.move_up()

    def advance_perpendicular(self):
        self.switch_direction()
        self.advance()
        self.switch_direction()

    def retreat_perpendicular(self):
        self.switch_direction()
        self.retreat()
        self.switch_direction()

    def advance_within_word(self, overwrite_mode=False, wrap_mode=False):
        within_pos = self.move_within_word(overwrite_mode, wrap_mode)
        if within_pos:
            self.position = within_pos
        else:
            self.advance_to_next_word(blank_placement=True)

    def move_within_word(self, overwrite_mode=False, wrap_mode=False):
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
        word_group = self.grid.words[self.direction]
        next_words = (self.grid.words['across'] if self.direction == 'down'
                      else self.grid.words['down'])

        while self.current_word() not in word_group:
            self.retreat()

        word_index = word_group.index(self.current_word())

        if word_index == len(word_group) - 1:
            self.switch_direction()
            self.position = next_words[0][0]
        else:
            self.position = word_group[word_index + 1][0]

        earliest_blank = self.earliest_blank_in_word()

        # If there are no blank squares left, override
        # the blank_placement setting
        if blank_placement and not self.grid.blank_cells_remaining:
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

        word_group = self.grid.words[self.direction]
        next_words = (self.grid.words['across'] if self.direction == 'down'
                      else self.grid.words['down'])

        while self.current_word() not in word_group:
            self.advance()

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
        if blank_placement and not self.grid.blank_cells_remaining:
            blank_placement = False

        if blank_placement and self.earliest_blank_in_word():
            self.position = self.earliest_blank_in_word()
        elif blank_placement and not self.earliest_blank_in_word():
            self.retreat_to_previous_word(end_placement, blank_placement)

    def earliest_blank_in_word(self):
        blanks = (pos for pos in self.current_word()
                  if self.grid.cells.get(pos).is_blankish)
        return next(blanks, None)

    def move_right(self):
        spaces = self.grid.spaces['across']
        current_space = spaces.index(self.position)
        ordered_spaces = spaces[current_space + 1:] + spaces[:current_space]

        return next(iter(ordered_spaces))

    def move_left(self):
        spaces = self.grid.spaces['across']
        current_space = spaces.index(self.position)
        ordered_spaces = (spaces[current_space - 1::-1] +
                          spaces[:current_space:-1])

        return next(iter(ordered_spaces))

    def move_down(self):
        spaces = self.grid.spaces['down']
        current_space = spaces.index(self.position)
        ordered_spaces = spaces[current_space + 1:] + spaces[:current_space]

        return next(iter(ordered_spaces))

    def move_up(self):
        spaces = self.grid.spaces['down']
        current_space = spaces.index(self.position)
        ordered_spaces = (spaces[current_space - 1::-1] +
                          spaces[:current_space:-1])

        return next(iter(ordered_spaces))

    def current_word(self):
        pos = self.position

        word = next((w for w in self.grid.words[self.direction] if pos in w),
                    [pos])

        return word

    def go_to_numbered_square(self):
        num = self.grid.get_notification_input("Enter square number:",
                                               input_condition=str.isdigit)
        if num:
            pos = next((pos for pos in self.grid.cells
                        if self.grid.cells.get(pos).number == int(num)), None)
            if pos:
                self.position = pos
                self.grid.send_notification(
                    "Moved cursor to square {}.".format(num))
            else:
                self.grid.send_notification("Not a valid number.")
        else:
            self.grid.send_notification("No valid number entered.")


class Timer(threading.Thread):
    def __init__(self, grid, starting_seconds=0, is_running=True, active=True):
        self.starting_seconds = starting_seconds
        self.is_running = is_running
        self.active = active
        self.time_passed = 0
        self.start_time = 0

        super().__init__(daemon=True)

        self.grid = grid

    def run(self):
        self.start_time = time.time()
        self.time_passed = self.starting_seconds

        self.show_time()

        while self.active:
            if self.is_running:
                self.time_passed = (self.starting_seconds +
                                    int(time.time() - self.start_time))
                self.show_time()

            time.sleep(0.5)

    def show_time(self):
        y_coord = 2
        x_coord = self.grid.grid_x + self.grid.column_count * 4 - 7

        echo(self.grid.term.move(y_coord, x_coord) +
             self.display_format())

    def display_format(self):
        time_amount = self.time_passed

        m, s = divmod(time_amount, 60)
        h, m = divmod(m, 60)

        ch = '{h:02d}:'.format(h=h) if h else '   '
        time_string = '{ch}{m:02d}:{s:02d}'.format(ch=ch, m=m, s=s)

        return time_string

    def save_format(self):
        time_amount = self.time_passed

        save_string = '{t},{r}'.format(
            t=int(time_amount), r=int(self.active))

        save_bytes = save_string.encode(puz.ENCODING)

        return save_bytes

    def pause(self):
        self.is_running = False

    def unpause(self):
        self.starting_seconds = self.time_passed
        self.start_time = time.time()
        self.is_running = True


def main():
    version_dir = os.path.abspath(os.path.dirname((__file__)))
    version_file = os.path.join(version_dir, 'version')
    with open(version_file) as f:
        version = f.read().strip()

    parser = argparse.ArgumentParser(
        prog='cursewords',
        description="""cursewords is a terminal-based crossword puzzle
        solving interface. Use it to open, solve, and save puzzles in the
        standard AcrossLite .puz format. Arrow keys and tab navigate,
        and space bar switches the cursor direction.""",
        usage=textwrap.dedent("""\
            cursewords [-h] [--downs-only] [--version] PUZfile
            print mode: cursewords [--print] [--blank | --solution] [--width INT] PUZfile"""))

    parser.add_argument('filename', metavar='PUZfile',
                        help="""path of puzzle file in the \
                        AcrossLite .puz format""")
    parser.add_argument('--downs-only', action='store_true',
                        help="""displays only the down clues""")

    print_group = parser.add_argument_group('print mode', description="""\
        If the --print flag is explicitly provided, or if cursewords
        is not running in an interactive terminal (because its
        output is being piped or redirected), print a formatted
        grid and set of clues to stdout instead of starting an interactive
        session.""")
    print_group.add_argument('--print', action='store_true', help="""\
        output formatted grid and clues to stdout""")

    print_fill = print_group.add_mutually_exclusive_group()
    print_fill.add_argument('--blank', action='store_true', help="""\
        format the puzzle grid with no answers""")
    print_fill.add_argument('--solution', action='store_true', help="""\
        format the puzzle grid with a filled solution""")

    print_group.add_argument('--width', action='store', type=int, help="""\
        maximum width in characters of the output (default 92)""")

    parser.add_argument('--version', action='version', version=version)

    args = parser.parse_args()
    filename = args.filename
    downs_only = args.downs_only
    print_mode = args.print or not sys.stdout.isatty()
    print_style = ('solution' if args.solution
                   else 'blank' if args.blank
                   else None)
    print_width = args.width

    try:
        puzfile = puz.read(filename)
    except:
        sys.exit("Unable to parse {} as a .puz file.".format(filename))

    term = Terminal()

    grid_x = 2
    grid_y = 4

    grid = Grid(grid_x, grid_y, term)
    grid.load(puzfile)

    if print_mode:
        printer_output(grid, style=print_style, width=print_width,
                       downs_only=downs_only)
        sys.exit()

    puzzle_width = max(4 * grid.column_count, 40)
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

    echo(term.enter_fullscreen())
    echo(term.clear())

    software_info = 'cursewords v{}'.format(version)
    puzzle_info = '{grid.title} - {grid.author}'.format(grid=grid)
    padding = 2
    sw_width = len(software_info) + 5
    pz_width = term.width - sw_width - padding
    if len(puzzle_info) > pz_width:
        puzzle_info = "{}…".format(puzzle_info[:pz_width - 1])

    headline = " {:<{pz_w}}{:>{sw_w}} ".format(
        puzzle_info, software_info,
        pz_w=pz_width, sw_w=sw_width)

    with term.location(x=0, y=0):
        echo(term.dim + term.reverse(headline) + term.normal)

    grid.draw()


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
            echo(toolbar)
    else:
        grid.notification_area = (grid.notification_area[0] - 1, grid_x)
        command_split = int(len(commands)/2) - 1
        for idx, (shortcut, action) in enumerate(commands):
            shortcut = term.reverse(shortcut)
            toolbar += "{:<25}".format(' '.join([shortcut, action]))

            if idx == command_split:
                toolbar += '\n' + grid_x * ' '

        with term.location(x=grid_x, y=term.height - 2):
            echo(toolbar)

    clue_width = min(int(1.3 * (puzzle_width) - grid_x),
                     term.width - 2 - grid_x)

    clue_wrapper = textwrap.TextWrapper(
        width=clue_width,
        max_lines=3,
        subsequent_indent=grid_x * ' ')

    start_pos = grid.words['across'][0][0]
    cursor = Cursor(start_pos, "across", grid)

    old_word = []
    old_position = start_pos
    keypress = ''
    puzzle_paused = False
    puzzle_complete = False
    modified_since_save = False
    to_quit = not sys.stdout.isatty()

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
                if cursor.current_word() in grid.words[cursor.direction]:
                    num_index = grid.words[cursor.direction].index(
                        cursor.current_word())
                    clue = grid.clues[cursor.direction][num_index]['clue']
                    if cursor.direction == 'across' and downs_only:
                        clue = "—"
                else:
                    clue = ""

                num = (str(grid.cells.get(cursor.current_word()[0]).number)
                       if clue else "")

                compiled_clue = (num + " " + cursor.direction.upper() +
                                 ": " + clue) if num else ""
                wrapped_clue = clue_wrapper.wrap(compiled_clue)
                wrapped_clue += [''] * (3 - len(wrapped_clue))
                wrapped_clue = [line + term.clear_eol for line in wrapped_clue]

                # This is fun: since we're in raw mode, \n isn't sufficient to
                # return the printing location to the first column. If you
                # don't also have \r,
                # it
                #    prints
                #           like
                #                this after each newline
                echo(term.move(info_location['y'], info_location['x']) +
                     '\r\n'.join(wrapped_clue))

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
                    echo(term.reverse("You've completed the puzzle! 🎉"),
                         term.clear_eol)
                timer.show_time()
                timer.active = False

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
                    grid.draw(empty=True)

                    with term.location(**info_location):
                        echo('\r\n'.join(['PUZZLE PAUSED' + term.clear_eol,
                                          term.clear_eol,
                                          term.clear_eol]))

                    puzzle_paused = True

                else:
                    timer.unpause()
                    grid.draw()
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
                            cell.corrected = False
                            cell.revealed = False
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
                    "Check (l)etter, (w)ord, or (p)uzzle?",
                    char_limit=1)
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
                    "Reveal (l)etter, (w)ord, or (p)uzzle?",
                    char_limit=1)
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

                if current_cell.marked_wrong:
                    current_cell.marked_wrong = False
                    current_cell.corrected = True
                modified_since_save = True
                cursor.advance_within_word(overwrite_mode, wrap_mode=True)

            # Deletion keys
            elif (not puzzle_complete and
                  keypress.name in ['KEY_BACKSPACE', 'KEY_DELETE']):
                current_cell.clear()
                overwrite_mode = True
                modified_since_save = True
                if keypress.name == 'KEY_BACKSPACE':
                    cursor.retreat_within_word(end_placement=True)
                elif keypress.name == 'KEY_DELETE':
                    cursor.advance_within_word(overwrite_mode=True)

            # Navigation
            elif (keypress.name in ['KEY_TAB'] or
                  (cursor.direction == "across" and
                   keypress.name == "KEY_SRIGHT") or
                  (cursor.direction == "down" and
                   keypress.name == "KEY_SDOWN")):
                if current_cell.is_blankish:
                    cursor.advance_to_next_word(blank_placement=True)
                else:
                    cursor.advance_within_word(overwrite_mode=False)

            elif keypress.name in ['KEY_PGDOWN']:
                cursor.advance_to_next_word()

            elif (keypress.name in ['KEY_BTAB'] or
                  (cursor.direction == "across" and
                   keypress.name == "KEY_SLEFT") or
                  (cursor.direction == "down" and
                   keypress.name == "KEY_SUP")):
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

            elif (keypress in ['}', ']'] or
                  (cursor.direction == "across" and
                   keypress.name == 'KEY_SDOWN') or
                  (cursor.direction == "down" and
                   keypress.name == 'KEY_SRIGHT')):
                cursor.advance_perpendicular()

                if (keypress == '}' and grid.blank_cells_remaining):
                    while not grid.cells.get(cursor.position).is_blankish:
                        cursor.advance_perpendicular()

            elif (keypress in ['{', '['] or
                  (cursor.direction == "across" and
                   keypress.name == 'KEY_SUP') or
                  (cursor.direction == "down" and
                   keypress.name == 'KEY_SLEFT')):
                cursor.retreat_perpendicular()

                if (keypress == '{' and grid.blank_cells_remaining):
                    while not grid.cells.get(cursor.position).is_blankish:
                        cursor.retreat_perpendicular()

    echo(term.exit_fullscreen())


if __name__ == '__main__':
    main()
