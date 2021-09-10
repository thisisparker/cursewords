# cursewords

`cursewords` is a "graphical" command line program for solving crossword puzzles in the terminal. You can use it to open, solve, and save puzzle files in the popular AcrossLite .puz format.

<img src="https://raw.githubusercontent.com/thisisparker/cursewords/master/demo.gif" width=450px>

## Installation

`cursewords` is only compatible with `python3`, and can be installed on through `pip`. If you don't know what that means, the best command is probably:

```bash
pip3 install cursewords
```

You should then be ready to go. You can then use  `cursewords` to open `.puz` files directly:

```
cursewords todaysnyt.puz
```

`cursewords` has been tested to work on Linux, Mac, and Windows computers.

## Usage

Controls are printed in a panel at the bottom of the screen. Note that (for now) `cursewords` is not very accommodating of changes in window size, so you may have to quit and re-open if you need to resize your terminal.

### Navigation

If you've used a program to solve crossword puzzles, navigation should be pretty intuitive. `tab` and `shift+tab` are the workhorses for navigation between blanks. Arrow keys will navigate the grid according to the direction of the cursor, and `shift+arrow` will move through words perpendicular to the cursor. `page up` and `page down` (on Mac, `Fn+` up/down arrow keys) jump between words without considering blank spaces. `ctrl+g`, followed by a number, will jump directly to the space with that number.

If you need some help, `ctrl+c` will check the current square, word, or entire puzzle for errors, and `ctrl+r` will reveal answers (subject to the same scoping options). To clear all entries on the puzzle, use `ctrl+x`, and to reset the puzzle to its original state (resetting the timer and removing any stored information about hints and corrections), use `ctrl+z`.

To open a puzzle in `downs-only` mode, where only the down clues are visible, use the `--downs-only` flag when opening the file on the command line.

### Print mode

If `cursewords` is not running in an interactive terminal (because its output is being piped to another command or redirected to a file) or if you pass the `--print` flag directly, it will print a formatted grid and list of clues to stdout and quit. The output of that command can be modified with the following flags:

* `--blank` ensures the grid is unfilled, even if you've saved solving progress
* `--solution` prints the filled grid
* `--width INT` caps the program output at INT characters wide. (If this flag isn't passed at runtime, `cursewords` will attempt to pick a reasonable output size. In many cases that will be 92 characters or the width of the puzzle.)
