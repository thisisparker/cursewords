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

small_nums = str.maketrans('1234567890',
                           '₁₂₃₄₅₆₇₈₉₀')
encircle = str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZ ',
                         'ⒶⒷⒸⒹⒺⒻⒼⒽⒾⒿⓀⓁⓂⓃⓄⓅⓆⓇⓈⓉⓊⓋⓌⓍⓎⓏ◯')
