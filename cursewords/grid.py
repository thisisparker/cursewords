#! /usr/bin/env python3

"""
This is the grid itself.
"""

# pylint: disable=too-many-arguments
# pylint: disable=too-many-branches
# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-public-methods

from . import chars


class Cell:
    """ One cell of the grid """

    CORRECTED = 0x10
    MARKED_WRONG = 0x20
    REVEALED = 0x40
    CIRCLED = 0x80

    def __init__(self, solution, entry=None):
        self.solution = solution
        self.metadata = 0

        self.number = None
        if entry:
            self.entry = entry
        else:
            self.entry = "-"

    def __str__(self):
        return self.entry

    def clear(self):
        """ clear this cell's metadata """
        self.entry = "-"
        if self.is_marked_wrong:
            self.metadata = Cell.CORRECTED
        else:
            self.metadata = 0

    def _set(self, bit, status):
        if status:
            self.metadata |= bit
        else:
            self.metadata &= ~bit

    @property
    def is_marked_wrong(self):
        """ is the answer wrong? """
        return bool(self.metadata & Cell.MARKED_WRONG)

    def set_marked_wrong(self, val):
        """ set our wrong answer flag """
        self._set(Cell.MARKED_WRONG, bool(val))

    @property
    def is_corrected(self):
        """ has the answer been corrected? """
        return bool(self.metadata & Cell.CORRECTED)

    def set_corrected(self, val):
        """ set our corrected flag """
        self._set(Cell.CORRECTED, bool(val))

    @property
    def is_revealed(self):
        """ has our answer been revealed? """
        return bool(self.metadata & Cell.REVEALED)

    def set_revealed(self, val):
        """ set our revealed flag """
        self._set(Cell.REVEALED, bool(val))

    @property
    def is_circled(self):
        """ is our box circled? """
        return bool(self.metadata & Cell.CIRCLED)

    def set_circled(self, val):
        """ set our circled flag """
        self._set(Cell.CIRCLED, bool(val))

    @property
    def is_block(self):
        """ test if this cell is a block """
        return self.solution == "."

    @property
    def is_letter(self):
        """ test if this cell is a letter """
        return self.solution.isalnum()

    @property
    def is_blank(self):
        """ test if this cell is blank """
        return self.entry == "-"

    @property
    def is_blankish(self):
        """ test if we should treat this cell as blank """
        return self.is_blank or self.is_marked_wrong

    @property
    def is_correct(self):
        """ test if this cell is filled in correctly """
        return self.is_block or self.entry == self.solution

    def compile(self):
        """ compile the various attributes of one cell """

        if self.is_blank:
            value = " "
        else:
            value = self.entry

        if self.is_circled:
            value = chars.encircle(value)

        return value


class Grid:
    """ This represents our abstract grid """

    def __init__(self, grid_x, grid_y):
        self.x = grid_x # pylint: disable=invalid-name
        self.y = grid_y # pylint: disable=invalid-name
        self.puzfile = None
        self.cells = {}
        self.row_count = 0
        self.column_count = 0
        self.title = ''
        self.author = ''

        self.across_words = []
        self.down_words = []
        self.across_clues = []
        self.down_clues = []

        self.start_time = 0
        self.timer_active = False
        self.notification_timer = None

    @property
    def down_words_grouped(self):
        """ get our down word groups """
        return sorted(self.down_words,
                      key=lambda word: (word[0][1], word[0][0]))

    def load(self, puzfile):
        """" load our grid from a file """
        self.puzfile = puzfile
        self.cells = {}
        self.row_count = puzfile.height
        self.column_count = puzfile.width

        self.title = puzfile.title
        self.author = puzfile.author

        for i in range(self.row_count):
            for j in range(self.column_count):
                idx = i * self.column_count + j
                entry = self.puzfile.fill[idx]
                self.cells[(j, i)] = Cell(self.puzfile.solution[idx], entry)

        self.across_words = []
        for i in range(self.row_count):
            current_word = []
            for j in range(self.column_count):
                if self.cells[(j, i)].is_letter:
                    current_word.append((j, i))
                elif len(current_word) > 1:
                    self.across_words.append(current_word)
                    current_word = []
                elif current_word:
                    current_word = []
            if len(current_word) > 1:
                self.across_words.append(current_word)

        self.down_words = []
        for j in range(self.column_count):
            current_word = []
            for i in range(self.row_count):
                if self.cells[(j, i)].is_letter:
                    current_word.append((j, i))
                elif len(current_word) > 1:
                    self.down_words.append(current_word)
                    current_word = []
                elif current_word:
                    current_word = []
            if len(current_word) > 1:
                self.down_words.append(current_word)

        num = self.puzfile.clue_numbering()
        self.across_clues = [word['clue'] for word in num.across]
        self.down_clues = [word['clue'] for word in num.down]

        if self.puzfile.has_markup():
            markup = self.puzfile.markup().markup

            for metadata, pos in zip(markup, self.cells):
                cell = self.cells.get(pos)
                cell.metadata = metadata

    def number(self):
        """ number the grid """
        numbered_squares = []
        for word in self.across_words:
            numbered_squares.append(word[0])

        for word in self.down_words:
            if word[0] not in numbered_squares:
                numbered_squares.append(word[0])

        numbered_squares.sort(key=lambda x: (x[1], x[0]))

        for number, square in enumerate(numbered_squares, 1):
            self.cells.get(square).number = number

    def save(self, filename):
        """ save the puzzle so the user can curse at it more later """
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

        if (any(self.cells.get(pos).is_marked_wrong or
                self.cells.get(pos).is_corrected
                for pos in self.cells) or
                self.puzfile.has_markup()):
            metadata = []
            for pos in self.cells:
                cell = self.cells[pos]
                metadata.append(cell.metadata)

            self.puzfile.markup().markup = metadata

        self.puzfile.save(filename)

    def make_row(self, leftmost, middle, divider, rightmost):
        """ make an arbitrary row """
        row = leftmost
        for col in range(1, self.column_count * 4):
            new_char = divider if col % 4 == 0 else middle
            row += new_char
        row += rightmost
        return row

    def get_top_row(self):
        """ get the top row """
        return self.make_row(chars.ulcorner, chars.hline, chars.ttee, chars.urcorner)

    def get_bottom_row(self):
        """ get the bottom row """
        return self.make_row(chars.llcorner, chars.hline, chars.btee, chars.lrcorner)

    def get_middle_row(self):
        """ get a row in the middle """
        return self.make_row(chars.vline, " ", chars.vline, chars.vline)

    def get_divider_row(self):
        """ get a divider row """
        return self.make_row(chars.ltee, chars.hline, chars.bigplus, chars.rtee)

# -*- coding: utf-8 -*-
# vim:fenc=utf-8:tw=75
