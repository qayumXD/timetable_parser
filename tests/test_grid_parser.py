from src.parser.grid_parser import parse_grid


def test_parse_grid_skips_break_and_maps_days():
    raw_table = [
        [None, "1\n8:30-10:00AM", "2\n10:00-11:30AM", "3\n11:30AM-1:00PM", "Break\n1:00-1:30PM", "4\n1:30-3:00PM", "5\n3:00-4:30PM", "6\n4:30-6:00PM"],
        ["Monday", "A", "B", "C", "", "D", "E", "F"],
        ["Tuesday", "", "", "", "", "", "", ""],
    ]

    grid = parse_grid(raw_table)

    assert grid["Monday"][1] == "A"
    assert grid["Monday"][3] == "C"
    assert grid["Monday"][4] == "D"
    assert grid["Monday"][6] == "F"
    assert grid["Tuesday"][2] == ""
