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
