# cursewords

`cursewords` is a "graphical" command line program for solving crossword puzzles in the terminal. It can be used to open files saved in the widely used AcrossLite `.puz` format.

![An animated demo of cursewords in action.](demo.gif)

`cursewords` includes nearly every major feature you might expect in a crossword program, including:

* intuitive navigation
* answer-checking for squares, words, and full puzzles
* a pausable puzzle timer
* a puzzle completeness notification

It is currently under active development, and should not be considered fully "released." That said, it is stable and suitable for everyday use.

## Installation

To install `cursewords`, make sure you have `python3.6` or similar. (I haven't extensively tested, but it should likely work with `3.4` and higher.) Clone this repo and change into the new directory, and then use pip to install the dependencies:

```bash
pip3 install -r requirements.txt
```

You should then be ready to go. For now, use `cursewords` to open `.puz` files directly:

```
./cursewords.py todaysnyt.puz
```

## Usage

If you've used a program to solve crossword puzzles, navigation should be pretty intuitive. `tab` and `shift+tab` are the workhorses for navigation between blanks. `page up` and `page down` (on Mac, `ctrl+` arrow keys) jump between words without considering blank spaces. `ctrl+g`, followed by a number, will jump directly to the space with that number.

If you need some help, `ctrl+c` will check the current square, word, or entire puzzle for errors.
