"""
XOR Monochrome Puzzle Game
==========================
A puzzle game where you overlap black pieces using XOR logic:
  black + black = white (cancel out)
  black + white = black (stays black)

Level difficulty: 0 (easiest) to 100 (hardest)
"""

import argparse
import sys

from game import Game
from generation import generate_level


def print_solution(level: int):
    data = generate_level(level)
    print(f"\nLevel {level} Solution")
    print(f"Grid size : {data['grid_size']}x{data['grid_size']}")
    print(f"Pieces    : {data['num_pieces']}")
    print()
    print("Target grid (1=black):")
    for row in data["target"]:
        print("  " + " ".join("█" if v else "·" for v in row))
    print()
    print("Piece placements (col, row from top-left = 0,0):")
    for i, (gc, gr) in enumerate(data["solution"]):
        piece = data["pieces"][i]
        min_r, min_c, max_r, max_c = piece.bounding_box()
        print(
            f"  Piece {i+1}: place at col={gc}, row={gr}  "
            f"(size {max_c-min_c+1}×{max_r-min_r+1})"
        )


def main():
    parser = argparse.ArgumentParser(description="XOR Monochrome Puzzle Game")
    parser.add_argument("--level", type=int, default=1, help="Starting level (0-100, default 1)")
    parser.add_argument("--print-solution", type=int, default=None, help="Print solution for a given level and exit")
    args = parser.parse_args()

    if args.print_solution is not None:
        print_solution(args.print_solution)
        sys.exit(0)

    game = Game()
    game.current_level = max(0, min(100, args.level))
    game.load_level(game.current_level)
    game.run()


if __name__ == "__main__":
    main()
