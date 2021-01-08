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

smallify_numbers = str.maketrans('0123456789', '₀₁₂₃₄₅₆₇₈₉')
encircle_letters = str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZ ',
                                 'ⒶⒷⒸⒹⒺⒻⒼⒽⒾⒿⓀⓁⓂⓃⓄⓅⓆⓇⓈⓉⓊⓋⓌⓍⓎⓏ◯')

