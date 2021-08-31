# cursewords

`cursewords` is a "graphical" command line program for solving crossword puzzles in the terminal. It can be used to open files saved in the widely used AcrossLite `.puz` format.

<img src="https://raw.githubusercontent.com/thisisparker/cursewords/master/demo.gif" width=450px>

`cursewords` includes nearly every major feature you might expect in a crossword program, including:

* intuitive navigation
* answer-checking for squares, words, and full puzzles
* a pausable puzzle timer
* a puzzle completeness notification

It is currently under active development, and should not be considered fully "released." That said, it is stable and suitable for everyday use.

## Installation

`cursewords` is only compatible with `python3`, and can be installed through `pip`. If you don't know what that means, the best command is probably:

```bash
pip3 install --user cursewords
```

You should then be ready to go. You can then use  `cursewords` to open `.puz` files directly:

```
cursewords todaysnyt.puz
```

## Usage

If you've used a program to solve crossword puzzles, navigation should be pretty intuitive. `tab` and `shift+tab` are the workhorses for navigation between blanks. Arrow keys will navigate the grid according to the direction of the cursor, and `shift+arrow` will move through words perpendicular to the cursor. `page up` and `page down` (on Mac, `Fn+` up/down arrow keys) jump between words without considering blank spaces. `ctrl+g`, followed by a number, will jump directly to the space with that number.

If you need some help, `ctrl+c` will check the current square, word, or entire puzzle for errors, and `ctrl+r` will reveal answers (subject to the same scoping options). To clear all entries on the puzzle, use `ctrl+x`, and to reset the puzzle to its original state (resetting the timer and removing any stored information about hints and corrections), use `ctrl+z`.

To open a puzzle in `downs-only` mode, where only the down clues are visible, use the `--downs-only` flag when opening the file on the command line.
