#! /usr/bin/env python3

import random
import string
import sys

import puz

from blessed import Terminal

from characters import *

grid_x = 4
grid_y = 2
rows = 15
columns = 15

term = Terminal()

class Cell:
    def __init__(self, x_pos, y_pos, solution):
        self.x_pos = x_pos
        self.y_pos = y_pos

        self.solution = solution

        self.number = None
        self.entry = None

    def is_block(self):
        return self.solution == "."

    def is_letter(self):
        return self.solution in string.ascii_uppercase

def main():
    print(term.enter_fullscreen())

    filename = sys.argv[1]
    data = puz_load(filename)
    
    print(term.clear())

    make_grid(grid_x, grid_y)
        
    number_grid(data)
    fill_grid(data)

    ctrl = ''

    with term.cbreak():
        while ctrl != 'q':
            ctrl = term.getch()

    print(term.exit_fullscreen())

def puz_load(puzfile):
    try:
        p = puz.read(puzfile)
    except:
        exit("Not a valid puzzle file.")

    puzzle = []
    for i in range(15):
        row = []
        for j in range(15):
            row.append(Cell(i, j, p.solution[i*rows + j]))
        puzzle.append(row)

    return puzzle

def number_grid(data):
    number = 1
    for rownum, row in enumerate(data):
        for col, cell in enumerate(row):
            if not cell.is_block():
                if (cell.x_pos == 0 or cell.y_pos == 0):
                    cell.number = number
                    number += 1
                elif (data[rownum][col - 1].is_block() or 
                        data[rownum - 1][col].is_block()):
                    cell.number = number
                    number += 1

def fill_grid(data):
    for i, row in enumerate(data):
        row_y = grid_y + (i * 2) + 1
        for j, cell in enumerate(row):
            cell_x = grid_x + (j * 4) + 2
            if cell.is_letter():
                print(term.move(row_y, cell_x) + cell.solution)
            elif cell.is_block():
                print(term.move(row_y, cell_x - 1) + squareblock)

            if cell.number:
                small = small_nums(cell.number)
                x_pos = cell_x - 1 if len(small) == 2 else cell_x
                print(term.move(row_y-1, x_pos), small)

def small_nums(number):
    small_num = ""
    num_dict = {"1": "₁", "2": "₂", "3": "₃", "4": "₄", "5": "₅",
            "6": "₆", "7": "₇", "8": "₈", "9": "₉", "0": "₀" }
    for digit in str(number):
        small_num += num_dict[digit]

    return small_num


def make_grid(grid_x, grid_y):
    top_row = get_top_row()
    bottom_row = get_bottom_row()
    middle_row = get_middle_row()
    divider_row = get_divider_row()

    print(term.move(grid_y, grid_x) + top_row)
    for y_val in enumerate(range(grid_y + 1, grid_y + rows * 2), 1):
        if y_val[0] % 2 == 0:
            print(term.move(y_val[1], grid_x) + divider_row)
        else:
            print(term.move(y_val[1], grid_x) + middle_row)
    print(term.move(grid_y + rows * 2, grid_x) + bottom_row)

    return None

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

def make_junk_data():
    data = []
    for i in range(15):
        row = []
        for j in range(15):
            if random.randint(0, 2) != 2:
                new_char = random.choice(string.ascii_uppercase)
            else:
                new_char = "."
            box = Cell(i, j, new_char)
            row.append(box)
        data.append(row)

    return data

if __name__ == '__main__':
    main()
