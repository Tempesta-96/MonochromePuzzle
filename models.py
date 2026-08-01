from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class Piece:
    cells: List[Tuple[int, int]]
    grid_pos: Tuple[int, int]
    is_placed: bool = False
    dragging: bool = False
    drag_offset: Tuple[int, int] = (0, 0)
    drag_screen: Tuple[int, int] = (0, 0)

    def bounding_box(self):
        rows = [cell[0] for cell in self.cells]
        cols = [cell[1] for cell in self.cells]
        return min(rows), min(cols), max(rows), max(cols)

    def normalize(self):
        min_r = min(cell[0] for cell in self.cells)
        min_c = min(cell[1] for cell in self.cells)
        self.cells = [(r - min_r, c - min_c) for r, c in self.cells]

    def world_cells(self):
        gr, gc = self.grid_pos[1], self.grid_pos[0]
        return [(r + gr, c + gc) for r, c in self.cells]
