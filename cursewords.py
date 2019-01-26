#! /usr/bin/env python3

import string
import sys

import puz

from blessed import Terminal

from characters import *

term = Terminal()

class Cell:
    def __init__(self, solution, entry=None):
        self.solution = solution

        self.number = None
        if entry:
            self.entry = entry
        else:
            self.entry = " "

    def is_block(self):
        return self.solution == "."

    def is_letter(self):
        return self.solution in string.ascii_uppercase

class Grid:
    def __init__(self, grid_x, grid_y, puzfile):
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.puzfile = puzfile

        self.row_count = 15
        self.column_count = 15

    def load(self):
        self.cells = dict()
        for i in range(self.row_count):
            for j in range(self.column_count):
                self.cells[(j,i)] = Cell(
                        self.puzfile.solution[i * self.row_count + j])
        return None

    def draw(self):
        top_row = self.get_top_row()
        bottom_row = self.get_bottom_row()
        middle_row = self.get_middle_row()
        divider_row = self.get_divider_row()

        print(term.move(self.grid_y, self.grid_x) + top_row)
        for index, y_val in enumerate(range(self.grid_y + 1,
                                     self.grid_y + self.row_count * 2), 1):
            if index % 2 == 0:
                print(term.move(y_val, self.grid_x) + divider_row)
            else:
                print(term.move(y_val, self.grid_x) + middle_row)
        print(term.move(self.grid_y + self.row_count * 2, self.grid_x) 
              + bottom_row)
       
        return None

    def number(self):
        number = 1
        for x, y in self.cells:
            cell = self.cells[(x,y)]
            if not cell.is_block():
                if (x == 0 or y == 0):
                    cell.number = number
                    number += 1
                elif (self.cells[(x - 1, y)].is_block() or
                        self.cells[(x, y - 1)].is_block()):
                    self.cells[(x,y)].number = number
                    number += 1

        return None

    def fill(self):
        for position in self.cells:
            y_coord, x_coord = self.to_term(position)
            cell = self.cells[position]
            if cell.is_letter():
                print(term.move(y_coord, x_coord) + cell.solution)
            elif cell.is_block():
                print(term.move(y_coord, x_coord - 1) + squareblock)

            if cell.number:
                small = self.small_nums(cell.number)
                x_pos = x_coord - 1
                print(term.move(y_coord - 1, x_pos) + small)

        return None

    def to_term(self, position):
        point_x, point_y = position
        term_x = self.grid_x + (4 * point_x) + 2
        term_y = self.grid_y + (2 * point_y) + 1
        return (term_y, term_x)

    def small_nums(self, number):
        small_num = ""
        num_dict = {"1": "₁", "2": "₂", "3": "₃", "4": "₄", "5": "₅",
                    "6": "₆", "7": "₇", "8": "₈", "9": "₉", "0": "₀" }
        for digit in str(number):
            small_num += num_dict[digit]

        return small_num

    def make_row(self, leftmost, middle, divider, rightmost):
        row = leftmost
        for col in range(1, 60):
            new_char = divider if col % 4 == 0 else middle
            row += new_char
        row += rightmost
        return row

    def get_top_row(self):
        return self.make_row(ulcorner, hline, ttee, urcorner)

    def get_bottom_row(self):
        return self.make_row(llcorner, hline, btee, lrcorner)

    def get_middle_row(self):
        return self.make_row(vline, " ", vline, vline)

    def get_divider_row(self):
        return self.make_row(ltee, hline, bigplus, rtee)


class Cursor:
    def __init__(self, position, direction):
        self.position = position
        self.direction = direction

    def switch_direction(self, to=None):
        if to:
            self.direction = to
        elif self.direction == "across":
            self.direction = "down"
        elif self.direction == "down":
            self.direction = "across"

    def current_word(self, grid):
        pos = self.position
        word = []
        if self.direction == "across":
            while (not grid.cells[pos].is_block() and not 
                    self.is_off_grid(pos, grid)):
                word.append(pos)
                pos = (pos[0] + 1, pos[1])
        elif self.direction == "down":
            while (not grid.cells[pos].is_block() and not
                    self.is_off_grid(pos, grid)):
                word.append(pos)
                pos = (pos[0], pos[1] + 1)
        return word

    def is_off_grid(self, pos, grid):
        return (pos[0] < 0 or
                pos[0] > grid.row_count or
                pos[1] < 0 or
                pos[1] > grid.column_count)


def main():
    filename = sys.argv[1]
    try: 
        puzfile = puz.read(filename)
    except:
        sys.exit("Unable to parse {} as a .puz file.".format(filename))

    print(term.enter_fullscreen())
    print(term.clear())

    grid_x = 4
    grid_y = 2

    grid = Grid(grid_x, grid_y, puzfile)
    grid.load()
    grid.draw()
    grid.number()
    grid.fill()

    start_pos = [pos for pos in grid.cells if grid.cells[pos].is_letter()][0]
    cursor = Cursor(start_pos, "across")

    keypress = ''

    with term.cbreak(), term.hidden_cursor():
        while keypress != 'Q':
            # Debugging output here:
            with term.location(0, term.height - 3):
                print(repr(keypress) + " " +  str(cursor.current_word(grid))
                        + " " + str(cursor.direction).ljust(60))

            for position in cursor.current_word(grid):
                print(term.move(*grid.to_term(position)) +
                        term.underline(grid.cells.get(position).solution))

            term_pos = grid.to_term(cursor.position)
            value = grid.cells.get(cursor.position).solution
            print(term.move(*grid.to_term(cursor.position))
                    + term.blink(term.reverse(value)))

            keypress = term.inkey()

            if (cursor.direction == "across" and 
                    keypress.name in ['KEY_DOWN', 'KEY_UP']):
                
                for position in cursor.current_word(grid):
                    print(term.move(*grid.to_term(position)) +
                            grid.cells.get(position).solution)

                cursor.switch_direction("down")

            elif (cursor.direction == "down" and 
                    keypress.name in ['KEY_LEFT', 'KEY_RIGHT']):

                for position in cursor.current_word(grid):
                    print(term.move(*grid.to_term(position)) +
                            grid.cells.get(position).solution)

                cursor.switch_direction("across")

            elif (cursor.direction == "across" and
                    keypress.name == 'KEY_RIGHT'):

                cursor.position = (cursor.position[0] + 1, cursor.position[1])

    print(term.exit_fullscreen())

if __name__ == '__main__':
    main()
