#! /usr/bin/env python3

import collections
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
        self.entry = None

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
        self.cells = collections.OrderedDict()
        for i in range(self.row_count):
            for j in range(self.column_count):
                self.cells[(j,i)] = Cell(
                        self.puzfile.solution[i * self.row_count + j])
        return None

    def draw(self):
        top_row = get_top_row()
        bottom_row = get_bottom_row()
        middle_row = get_middle_row()
        divider_row = get_divider_row()

        print(term.move(self.grid_y, self.grid_x) + top_row)
        for y_val in enumerate(range(self.grid_y + 1, 
                                     self.grid_y + self.row_count * 2), 1):
            if y_val[0] % 2 == 0:
                print(term.move(y_val[1], self.grid_x) + divider_row)
            else:
                print(term.move(y_val[1], self.grid_x) + middle_row)
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
        for x, y in self.cells:
            y_coord = self.grid_y + (y * 2) + 1
            x_coord = self.grid_x + (x * 4) + 2
            cell = self.cells[(x,y)]
            if cell.is_letter():
                print(term.move(y_coord, x_coord) + cell.solution)
            elif cell.is_block():
                print(term.move(y_coord, x_coord - 1) + squareblock)

            if cell.number:
                small = small_nums(cell.number)
                x_pos = x_coord - 1
                print(term.move(y_coord - 1, x_pos) + small)

        return None


def small_nums(number):
    small_num = ""
    num_dict = {"1": "₁", "2": "₂", "3": "₃", "4": "₄", "5": "₅",
                "6": "₆", "7": "₇", "8": "₈", "9": "₉", "0": "₀" }
    for digit in str(number):
        small_num += num_dict[digit]

    return small_num

def make_row(leftmost, middle, divider, rightmost):
    row = leftmost
    for col in range(1, 60):
        new_char = divider if col % 4 == 0 else middle
        row += new_char
    row += rightmost
    return row

def get_top_row():
    return make_row(ulcorner, hline, ttee, urcorner)

def get_bottom_row():
    return make_row(llcorner, hline, btee, lrcorner)

def get_middle_row():
    return make_row(vline, " ", vline, vline)

def get_divider_row():
    return make_row(ltee, hline, bigplus, rtee)


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

    start_pos = [cell for cell in grid.cells if grid.cells[cell].is_letter()][0]

    ctrl = grid.cells.get(start_pos).solution

    with term.cbreak(), term.hidden_cursor(), term.keypad():
        while ctrl != 'Q':
            print(term.move(grid_y + 1, grid_x + 2) + term.reverse
                    + ctrl.upper())
            ctrl = term.inkey()

    print(term.exit_fullscreen())

if __name__ == '__main__':
    main()
