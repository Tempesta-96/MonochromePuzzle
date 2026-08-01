import copy
import random
from typing import Optional

from constants import GRID_COLS
from models import Piece


def rect_shape(w, h):
    return [(r, c) for r in range(h) for c in range(w)]


def tri_shape(size, direction="ne"):
    cells = []
    for r in range(size):
        for c in range(size):
            if direction == "ne" and c >= r:
                cells.append((r, c))
            elif direction == "nw" and c <= size - 1 - r:
                cells.append((r, c))
            elif direction == "se" and c <= r:
                cells.append((r, c))
            elif direction == "sw" and c >= size - 1 - r:
                cells.append((r, c))
    return cells


def l_shape(size):
    cells = [(r, 0) for r in range(size)] + [(size - 1, c) for c in range(1, size)]
    return list(set(cells))


def plus_shape(size):
    mid = size // 2
    cells = [(r, mid) for r in range(size)] + [(mid, c) for c in range(size)]
    return list(set(cells))


def checker_shape(size):
    return [(r, c) for r in range(size) for c in range(size) if (r + c) % 2 == 0]


SHAPE_GENERATORS = [
    lambda d: rect_shape(2, 2),
    lambda d: rect_shape(3, 2),
    lambda d: rect_shape(2, 3),
    lambda d: rect_shape(3, 3),
    lambda d: rect_shape(4, 2),
    lambda d: rect_shape(2, 4),
    lambda d: rect_shape(4, 3),
    lambda d: rect_shape(3, 4),
    lambda d: tri_shape(2, "ne"),
    lambda d: tri_shape(2, "nw"),
    lambda d: tri_shape(2, "se"),
    lambda d: tri_shape(2, "sw"),
    lambda d: tri_shape(3, "ne"),
    lambda d: tri_shape(3, "nw"),
    lambda d: tri_shape(3, "se"),
    lambda d: tri_shape(3, "sw"),
    lambda d: l_shape(3),
    lambda d: l_shape(4),
    lambda d: plus_shape(3),
    lambda d: checker_shape(3),
]


def difficulty_params(level: int):
    t = level / 100.0
    num_pieces = 2 + int(t * 6)
    grid_size = 4 + int(t * 4)
    grid_size = min(grid_size, GRID_COLS)
    return num_pieces, grid_size


def generate_level(level: int, seed: Optional[int] = None) -> dict:
    if seed is None:
        seed = level * 9999 + 42
    rng = random.Random(seed)

    num_pieces, grid_size = difficulty_params(level)
    pieces = []
    for _ in range(num_pieces):
        gen = rng.choice(SHAPE_GENERATORS)
        cells = gen(None)
        if level > 60 and rng.random() < 0.3:
            cells = rng.choice(SHAPE_GENERATORS[:8])(None)
        piece = Piece(cells=cells, grid_pos=(0, 0))
        piece.normalize()
        pieces.append(piece)

    solution = []
    for piece in pieces:
        min_r, min_c, max_r, max_c = piece.bounding_box()
        h = max_r - min_r + 1
        w = max_c - min_c + 1
        max_col = max(0, grid_size - w)
        max_row = max(0, grid_size - h)
        gc = rng.randint(0, max_col)
        gr = rng.randint(0, max_row)
        solution.append((gc, gr))

    target = [[0] * grid_size for _ in range(grid_size)]
    for piece, (gc, gr) in zip(pieces, solution):
        for dr, dc in piece.cells:
            rr, cc = gr + dr, gc + dc
            if 0 <= rr < grid_size and 0 <= cc < grid_size:
                target[rr][cc] ^= 1

    play_pieces = []
    for piece in pieces:
        clone = Piece(cells=copy.deepcopy(piece.cells), grid_pos=(0, 0))
        clone.normalize()
        play_pieces.append(clone)

    return {
        "target": target,
        "pieces": play_pieces,
        "solution": solution,
        "grid_size": grid_size,
        "level": level,
        "num_pieces": num_pieces,
    }


def compute_grid(pieces, grid_size: int):
    grid = [[0] * grid_size for _ in range(grid_size)]
    for piece in pieces:
        if piece.is_placed:
            for dr, dc in piece.cells:
                r = piece.grid_pos[1] + dr
                c = piece.grid_pos[0] + dc
                if 0 <= r < grid_size and 0 <= c < grid_size:
                    grid[r][c] ^= 1
    return grid
