import math
import sys
import textwrap

def printer_output(grid, style=None, width=None, downs_only=False):
    print_width = width or (92 if not sys.stdout.isatty()
                            else min(grid.term.width, 96))

    # Find the width in characters of the longest clue number
    max_num_width = max(len(str(entry['num'])) for entry in
                            (grid.clues['across'][-1], grid.clues['down'][-1]))

    # Create clue lists and store number and clue separately
    across_clues = [(entry['num'], entry['clue'].strip()) for entry in grid.clues['across']]
    down_clues = [(entry['num'], entry['clue'].strip()) for entry in grid.clues['down']]
    
    
    clue_lines = ['ACROSS', '']

    # Format across clues with aligned numbers
    for num, clue in across_clues:
        clue_lines.append(f"{num:>{max_num_width}}. {clue}")
    clue_lines.append('')

    if downs_only:
        clue_lines = []

    clue_lines.extend(['DOWN', ''])

    # Format down clues with aligned numbers
    for num, clue in down_clues:
        clue_lines.append(f"{num:>{max_num_width}}. {clue}")

    render_args = {'blank': style == 'blank', 'solution': style == 'solution'}

    grid_lines = [grid.term.strip(l) for l in
                  grid.render_grid(**render_args)]
    grid_lines.append('')

    if print_width < len(grid_lines[0]):
        sys.exit(f'Puzzle is {len(grid_lines[0])} columns wide, '
                 f'cannot be printed at {print_width} columns.')

    print_width = min(print_width, 2 * len(grid_lines[0]))

    print(f'{grid.title} - {grid.author}')
    print()

    current_clue = []
    current_line = ''
    f_width = print_width - len(grid_lines[0]) - 2

    if f_width > 12:
        while grid_lines:
            current_clue = (current_clue or
                            textwrap.wrap(clue_lines.pop(0), f_width,
                                          subsequent_indent=" " * (max_num_width + 2)) or
                            [''])
            current_line = current_clue.pop(0)
            current_grid_line = grid_lines.pop(0)
            print(f'{current_line:{f_width}.{f_width}}  {current_grid_line}')
    else:
        print('\n'.join(grid_lines))

    remainder = ' '.join(current_clue)
    if remainder:
        clue_lines.insert(0, remainder)

    wrapped_clue_lines = []
    num_cols = 3 if print_width > 64 else 2
    column_width = print_width // num_cols - 2
    
    for l in clue_lines:
        if l == '':
            wrapped_clue_lines.append('')
            continue

        indent_width = max_num_width + 2
            
        # Wrap the text
        lines = textwrap.wrap(l, width=column_width,
            subsequent_indent=" " * indent_width)
        wrapped_clue_lines.extend(lines)

    num_wrapped_rows = math.ceil(len(wrapped_clue_lines)/num_cols)

    for r in range(num_wrapped_rows):
        clue_parts = [wrapped_clue_lines[i] for i in
                      range(r, len(wrapped_clue_lines), num_wrapped_rows)]
        current_row = '  '.join([f'{{:{column_width}}}'] * len(clue_parts))
        print(current_row.format(*clue_parts))
