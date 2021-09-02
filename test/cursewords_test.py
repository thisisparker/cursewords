import cursewords

def test_format_time():
    test_cases = [
        (1,    "   00:01"),
        (61,   "   01:01"),
        (314,  "   05:14"),
        (1288, "   21:28"),
        (1288, "   21:28"),
        (3723, "01:02:03"),
    ]
    for (seconds, expect) in test_cases:
        assert cursewords.Timer.format_time(seconds) == expect
