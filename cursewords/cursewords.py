#! /usr/bin/env python3

"""
This modules builds us an interactive crossword puzle we can curse at
"""

import argparse
import os

from . import solving


def main():
    """ This is our main loop """
    version_dir = os.path.abspath(os.path.dirname((__file__)))
    version_file = os.path.join(version_dir, 'version')
    with open(version_file) as file:
        version = file.read().strip()

    parser = argparse.ArgumentParser(
        prog='cursewords',
        description="A terminal-based crossword puzzle solving interface.")

    parser.add_argument('filename', metavar='PUZfile',
                        help="path of AcrossLite .puz puzzle file")
    parser.add_argument('--downs-only', action='store_true',
                        help="""displays only the down clues""")
    parser.add_argument('--debug', action='store_true',
                        help="""run in debugging mode""")
    parser.add_argument('--version', action='version', version=version)

    args = parser.parse_args()
    filename = args.filename
    downs_only = args.downs_only
    debug = args.debug

    solver = solving.Solver(filename, version, downs_only, debug)
    solver.solve()


if __name__ == '__main__':
    main()
