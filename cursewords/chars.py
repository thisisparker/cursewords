#!/usr/bin/env python3

"""
Just some helpers for character printing
"""

# pylint: disable=invalid-name

vline = "│"
hline = "─"

llcorner = "└"
ulcorner = "┌"
lrcorner = "┘"
urcorner = "┐"

ttee = "┬"

btee = "┴"
ltee = "├"
rtee = "┤"

bigplus = "┼"

lhblock = "▌"
rhblock = "▐"
fullblock = "█"
squareblock = rhblock + fullblock + lhblock


def small_nums(number):
    """ tiny versions of normal numbers """

    small_num = ""
    num_dict = {"1": "₁", "2": "₂", "3": "₃", "4": "₄", "5": "₅",
                "6": "₆", "7": "₇", "8": "₈", "9": "₉", "0": "₀"}
    for digit in str(number):
        small_num += num_dict[digit]

    return small_num


def encircle(letter):
    """ unicode for circled letters """

    circle_dict = {"A": "Ⓐ", "B": "Ⓑ", "C": "Ⓒ", "D": "Ⓓ", "E": "Ⓔ", "F": "Ⓕ",
                   "G": "Ⓖ", "H": "Ⓗ", "I": "Ⓘ", "J": "Ⓙ", "K": "Ⓚ", "L": "Ⓛ",
                   "M": "Ⓜ", "N": "Ⓝ", "O": "Ⓞ", "P": "Ⓟ", "Q": "Ⓠ", "R": "Ⓡ",
                   "S": "Ⓢ", "T": "Ⓣ", "U": "Ⓤ", "V": "Ⓥ", "W": "Ⓦ", "X": "Ⓧ",
                   "Y": "Ⓨ", "Z": "Ⓩ", " ": "◯"}
    return circle_dict[letter]


# -*- coding: utf-8 -*-
# vim:fenc=utf-8:tw=75
