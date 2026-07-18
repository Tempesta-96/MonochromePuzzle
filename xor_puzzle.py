"""
XOR Monochrome Puzzle Game
==========================
A puzzle game where you overlap black pieces using XOR logic:
  black + black = white (cancel out)
  black + white = black (stays black)

Level difficulty: 0 (easiest) to 100 (hardest)
"""

import pygame
import sys
import random
import math
import copy
import json
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

# ── Constants ────────────────────────────────────────────────────────────────
SCREEN_W, SCREEN_H = 900, 700
GRID_COLS, GRID_ROWS = 8, 8
CELL = 48                        # pixels per grid cell
GRID_PIXEL = CELL * GRID_COLS    # 384 px
PREVIEW_SIZE = 160               # target preview box

TARGET_X = (SCREEN_W - GRID_PIXEL) // 2
TARGET_Y = 60
PLAY_X   = TARGET_X
PLAY_Y   = TARGET_Y + PREVIEW_SIZE + 40

BG        = (245, 242, 235)
BLACK     = (15,  12,  10)
WHITE     = (255, 255, 255)
GREY_LT   = (200, 195, 185)
GREY_MD   = (140, 133, 120)
ACCENT    = (220,  60,  40)
HIGHLIGHT = (80, 160, 255)
SHADOW    = (180, 175, 165)

FPS = 60

# ── Shape library ─────────────────────────────────────────────────────────────
# Each shape is a list of (row, col) offsets from origin (0,0)

def rect_shape(w, h):
    return [(r, c) for r in range(h) for c in range(w)]

def tri_shape(size, direction="ne"):
    """Right triangle. direction = ne/nw/se/sw"""
    cells = []
    for r in range(size):
        for c in range(size):
            if direction == "ne" and c >= r:      cells.append((r, c))
            elif direction == "nw" and c <= size-1-r: cells.append((r, c))
            elif direction == "se" and c <= r:    cells.append((r, c))
            elif direction == "sw" and c >= size-1-r: cells.append((r, c))
    return cells

def l_shape(size):
    cells = [(r, 0) for r in range(size)] + [(size-1, c) for c in range(1, size)]
    return list(set(cells))

def plus_shape(size):
    mid = size // 2
    cells = [(r, mid) for r in range(size)] + [(mid, c) for c in range(size)]
    return list(set(cells))

def checker_shape(size):
    return [(r, c) for r in range(size) for c in range(size) if (r+c) % 2 == 0]

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

# ── Piece ─────────────────────────────────────────────────────────────────────
@dataclass
class Piece:
    cells: List[Tuple[int,int]]   # list of (row,col) relative offsets
    grid_pos: Tuple[int,int]      # (col, row) on play grid — placed position
    is_placed: bool = False
    dragging: bool = False
    drag_offset: Tuple[int,int] = (0, 0)
    # screen pos while dragging
    drag_screen: Tuple[int,int] = (0, 0)

    def bounding_box(self):
        rows = [c[0] for c in self.cells]
        cols = [c[1] for c in self.cells]
        return min(rows), min(cols), max(rows), max(cols)

    def normalize(self):
        min_r = min(c[0] for c in self.cells)
        min_c = min(c[1] for c in self.cells)
        self.cells = [(r - min_r, c - min_c) for r, c in self.cells]

    def world_cells(self):
        """Cells in grid coords when placed."""
        gr, gc = self.grid_pos[1], self.grid_pos[0]
        return [(r + gr, c + gc) for r, c in self.cells]

# ── Level generation ──────────────────────────────────────────────────────────

def difficulty_params(level: int):
    """Return (num_pieces, grid_size) based on 0-100 difficulty."""
    t = level / 100.0
    # num pieces: 2..8
    num_pieces = 2 + int(t * 6)
    # grid cols/rows: 4..8
    grid_size = 4 + int(t * 4)
    grid_size = min(grid_size, GRID_COLS)
    return num_pieces, grid_size

def generate_level(level: int, seed: Optional[int] = None) -> dict:
    """
    Generate a level with a guaranteed solution.
    Returns {
        target: 2D list of 0/1,
        pieces: list of Piece objects (with solution positions),
        solution: list of (grid_col, grid_row) per piece,
        grid_size: int
    }
    """
    if seed is None:
        seed = level * 9999 + 42
    rng = random.Random(seed)

    num_pieces, grid_size = difficulty_params(level)

    # Build random pieces
    pieces = []
    for _ in range(num_pieces):
        gen = rng.choice(SHAPE_GENERATORS)
        cells = gen(None)
        # Scale small shapes on harder levels
        if level > 60 and rng.random() < 0.3:
            gen2 = rng.choice(SHAPE_GENERATORS[:8])   # rectangles only for scaling
            cells = gen2(None)
        p = Piece(cells=cells, grid_pos=(0, 0))
        p.normalize()
        pieces.append(p)

    # Assign random solution positions within grid
    solution = []
    for p in pieces:
        min_r, min_c, max_r, max_c = p.bounding_box()
        h = max_r - min_r + 1
        w = max_c - min_c + 1
        max_col = max(0, grid_size - w)
        max_row = max(0, grid_size - h)
        gc = rng.randint(0, max_col)
        gr = rng.randint(0, max_row)
        solution.append((gc, gr))

    # Compute target by XOR-ing all pieces at solution positions
    target = [[0] * grid_size for _ in range(grid_size)]
    for p, (gc, gr) in zip(pieces, solution):
        for (dr, dc) in p.cells:
            rr, cc = gr + dr, gc + dc
            if 0 <= rr < grid_size and 0 <= cc < grid_size:
                target[rr][cc] ^= 1

    # Scatter pieces to random non-solution starting positions for gameplay
    play_pieces = []
    for i, p in enumerate(pieces):
        np_ = Piece(cells=copy.deepcopy(p.cells), grid_pos=(0, 0))
        np_.normalize()
        play_pieces.append(np_)

    return {
        "target": target,
        "pieces": play_pieces,
        "solution": solution,
        "grid_size": grid_size,
        "level": level,
        "num_pieces": num_pieces,
    }

def compute_grid(pieces: List[Piece], grid_size: int):
    """XOR all placed pieces onto a grid."""
    grid = [[0] * grid_size for _ in range(grid_size)]
    for p in pieces:
        if p.is_placed:
            for (dr, dc) in p.cells:
                r = p.grid_pos[1] + dr
                c = p.grid_pos[0] + dc
                if 0 <= r < grid_size and 0 <= c < grid_size:
                    grid[r][c] ^= 1
    return grid

# ── Drawing helpers ───────────────────────────────────────────────────────────

def draw_grid(surf, grid, ox, oy, cell, show_dots=True):
    rows = len(grid)
    cols = len(grid[0]) if rows else 0
    # shadow
    pygame.draw.rect(surf, SHADOW,
                     (ox+4, oy+4, cols*cell, rows*cell), border_radius=4)
    # background
    pygame.draw.rect(surf, WHITE,
                     (ox, oy, cols*cell, rows*cell), border_radius=4)
    for r in range(rows):
        for c in range(cols):
            if grid[r][c]:
                pygame.draw.rect(surf, BLACK,
                                 (ox + c*cell, oy + r*cell, cell, cell))
    # grid lines / dots
    if show_dots:
        for r in range(rows+1):
            for c in range(cols+1):
                pygame.draw.circle(surf, GREY_LT,
                                   (ox + c*cell, oy + r*cell), 2)
    # border
    pygame.draw.rect(surf, GREY_MD,
                     (ox, oy, cols*cell, rows*cell), 2, border_radius=4)

def draw_piece_at_screen(surf, piece, sx, sy, cell, color=BLACK, alpha=255):
    """Draw a piece with top-left of bounding-box at (sx, sy)."""
    for (dr, dc) in piece.cells:
        rect = pygame.Rect(sx + dc*cell, sy + dr*cell, cell, cell)
        if alpha < 255:
            s = pygame.Surface((cell, cell), pygame.SRCALPHA)
            s.fill((*color, alpha))
            surf.blit(s, rect.topleft)
        else:
            pygame.draw.rect(surf, color, rect)

def draw_tray_piece(surf, piece, cx, cy, cell, selected=False):
    """Draw piece centred at (cx, cy)."""
    min_r, min_c, max_r, max_c = piece.bounding_box()
    h = (max_r - min_r + 1) * cell
    w = (max_c - min_c + 1) * cell
    sx = cx - w // 2 - min_c * cell
    sy = cy - h // 2 - min_r * cell
    color = HIGHLIGHT if selected else BLACK
    draw_piece_at_screen(surf, piece, sx, sy, cell, color=color)

def screen_to_grid(sx, sy, ox, oy, cell):
    return (sx - ox) // cell, (sy - oy) // cell   # col, row

def grid_to_screen(gc, gr, ox, oy, cell):
    return ox + gc * cell, oy + gr * cell

def grids_match(a, b):
    if len(a) != len(b): return False
    for ra, rb in zip(a, b):
        if ra != rb: return False
    return True

# ── Tray layout ───────────────────────────────────────────────────────────────
TRAY_Y = PLAY_Y + GRID_PIXEL + 20

def tray_positions(pieces: List[Piece], cell: int, top_y: int):
    """Lay out tray pieces in centred rows with spacing based on piece size."""
    if not pieces:
        return []

    horizontal_gap = 24
    vertical_gap = 28
    side_margin = 36
    max_row_width = SCREEN_W - side_margin * 2

    rows = []
    current_row = []
    current_width = 0

    for i, piece in enumerate(pieces):
        min_r, min_c, max_r, max_c = piece.bounding_box()
        piece_w = (max_c - min_c + 1) * cell
        piece_h = (max_r - min_r + 1) * cell
        entry = (i, piece_w, piece_h)
        entry_width = piece_w if not current_row else piece_w + horizontal_gap

        if current_row and current_width + entry_width > max_row_width:
            rows.append(current_row)
            current_row = [entry]
            current_width = piece_w
        else:
            current_row.append(entry)
            current_width += entry_width

    if current_row:
        rows.append(current_row)

    positions = [None] * len(pieces)
    y = top_y
    for row in rows:
        row_width = sum(piece_w for _, piece_w, _ in row) + horizontal_gap * max(0, len(row) - 1)
        row_height = max(piece_h for _, _, piece_h in row)
        x = (SCREEN_W - row_width) // 2

        for index, piece_w, piece_h in row:
            positions[index] = (x + piece_w // 2, y + row_height // 2)
            x += piece_w + horizontal_gap

        y += row_height + vertical_gap

    return positions

# ── Preview (scaled) ──────────────────────────────────────────────────────────
def draw_preview(surf, target, ox, oy, size):
    grid_size = len(target)
    cell = size // grid_size
    actual_w = cell * grid_size
    actual_h = cell * grid_size
    # centre
    px = ox + (size - actual_w) // 2
    py = oy + (size - actual_h) // 2
    pygame.draw.rect(surf, WHITE, (px, py, actual_w, actual_h))
    for r in range(grid_size):
        for c in range(grid_size):
            if target[r][c]:
                pygame.draw.rect(surf, BLACK,
                                 (px + c*cell, py + r*cell, cell, cell))
    pygame.draw.rect(surf, GREY_MD, (px, py, actual_w, actual_h), 2)

# ── UI Text ───────────────────────────────────────────────────────────────────
def draw_text(surf, text, x, y, font, color=BLACK, center=False):
    img = font.render(text, True, color)
    if center:
        x -= img.get_width() // 2
    surf.blit(img, (x, y))

# ── Button ────────────────────────────────────────────────────────────────────
class Button:
    def __init__(self, rect, label, font, color=BLACK, text_color=WHITE):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.font = font
        self.color = color
        self.text_color = text_color
        self.hovered = False

    def draw(self, surf):
        c = tuple(min(255, v+30) for v in self.color) if self.hovered else self.color
        pygame.draw.rect(surf, c, self.rect, border_radius=6)
        img = self.font.render(self.label, True, self.text_color)
        surf.blit(img, (self.rect.centerx - img.get_width()//2,
                        self.rect.centery - img.get_height()//2))

    def handle(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos):
            return True
        return False

# ── Solution overlay ──────────────────────────────────────────────────────────
def draw_solution_overlay(surf, level_data, ox, oy, cell, font_sm):
    grid_size = level_data["grid_size"]
    pieces    = level_data["pieces"]
    solution  = level_data["solution"]
    colors = [
        (220, 60, 40), (40, 120, 220), (40, 180, 80),
        (200, 140, 20), (140, 40, 200), (20, 180, 180),
        (220, 100, 180), (100, 100, 100),
    ]
    # darken bg
    overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    surf.blit(overlay, (0, 0))

    panel_w, panel_h = grid_size * cell + 160, grid_size * cell + 100
    px = (SCREEN_W - panel_w) // 2
    py = (SCREEN_H - panel_h) // 2
    pygame.draw.rect(surf, BG, (px, py, panel_w, panel_h), border_radius=10)
    pygame.draw.rect(surf, GREY_MD, (px, py, panel_w, panel_h), 2, border_radius=10)

    title = font_sm.render("SOLUTION", True, ACCENT)
    surf.blit(title, (px + panel_w//2 - title.get_width()//2, py + 12))

    gx = px + 80
    gy = py + 50

    # blank white grid
    pygame.draw.rect(surf, WHITE, (gx, gy, grid_size*cell, grid_size*cell))
    # draw each piece translucently
    for i, (p, (gc, gr)) in enumerate(zip(pieces, solution)):
        col = colors[i % len(colors)]
        for (dr, dc) in p.cells:
            r, c = gr + dr, gc + dc
            if 0 <= r < grid_size and 0 <= c < grid_size:
                s = pygame.Surface((cell, cell), pygame.SRCALPHA)
                s.fill((*col, 140))
                surf.blit(s, (gx + c*cell, gy + r*cell))
        lbl = font_sm.render(f"P{i+1}", True, col)
        surf.blit(lbl, (px + 10, gy + gr*cell + dr*cell // 2))

    pygame.draw.rect(surf, GREY_MD, (gx, gy, grid_size*cell, grid_size*cell), 2)
    hint = font_sm.render("Press S or click elsewhere to close", True, GREY_MD)
    surf.blit(hint, (px + panel_w//2 - hint.get_width()//2, py + panel_h - 28))

# ── Main Game ─────────────────────────────────────────────────────────────────

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("XOR Monochrome Puzzle")
        self.clock = pygame.time.Clock()

        self.font_lg  = pygame.font.SysFont("Georgia", 28, bold=True)
        self.font_md  = pygame.font.SysFont("Georgia", 20)
        self.font_sm  = pygame.font.SysFont("Georgia", 15)
        self.font_num = pygame.font.SysFont("Courier New", 24, bold=True)

        self.current_level = 1
        self.show_solution = False
        self.solved = False
        self.elapsed = 0.0
        self.moves = 0

        self.load_level(self.current_level)

        # Buttons
        bw, bh = 110, 34
        self.btn_prev    = Button((20, 20, bw, bh), "◀ PREV",   self.font_sm, BLACK)
        self.btn_next    = Button((SCREEN_W-130, 20, bw, bh), "NEXT ▶", self.font_sm, BLACK)
        self.btn_reset   = Button((20, SCREEN_H-60, bw, bh), "↺ RESET",  self.font_sm, (80, 80, 80))
        self.btn_hint    = Button((SCREEN_W-130, SCREEN_H-60, bw, bh), "💡 HINT", self.font_sm, (60, 130, 60))
        self.btn_level   = None   # slider-ish, handled separately

        self.dragging_piece: Optional[int] = None  # index into self.pieces
        self.drag_offset = (0, 0)

    # ── Level management ──────────────────────────────────────────────────────
    def load_level(self, level: int):
        self.current_level = max(0, min(100, level))
        data = generate_level(self.current_level)
        self.level_data = data
        self.target     = data["target"]
        self.grid_size  = data["grid_size"]
        self.solution   = data["solution"]

        # Deep-copy pieces for play
        self.pieces: List[Piece] = [
            Piece(cells=copy.deepcopy(p.cells), grid_pos=(0, 0))
            for p in data["pieces"]
        ]

        self.show_solution = False
        self.solved = False
        self.elapsed = 0.0
        self.moves = 0

        # Grid origin (centred)
        gs = self.grid_size
        self.ox = (SCREEN_W - gs * CELL) // 2
        self.oy = TARGET_Y + PREVIEW_SIZE + 50

        # Preview origin
        self.prev_ox = (SCREEN_W - PREVIEW_SIZE) // 2
        self.prev_oy = TARGET_Y

        # Arrange pieces in a tidy tray below the play grid.
        tray_top = self.oy + self.grid_size * CELL + 30
        self.tray_pos = tray_positions(self.pieces, CELL, tray_top)

    def check_solved(self):
        current = compute_grid(self.pieces, self.grid_size)
        return grids_match(current, self.target)

    # ── Events ────────────────────────────────────────────────────────────────
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()
                if event.key == pygame.K_s:
                    self.show_solution = not self.show_solution
                if event.key == pygame.K_r:
                    self.load_level(self.current_level)
                if event.key == pygame.K_RIGHT:
                    self.load_level(self.current_level + 1)
                if event.key == pygame.K_LEFT:
                    self.load_level(self.current_level - 1)

            # Buttons
            if self.btn_prev.handle(event):
                self.load_level(self.current_level - 1)
            if self.btn_next.handle(event):
                self.load_level(self.current_level + 1)
            if self.btn_reset.handle(event):
                self.load_level(self.current_level)
            if self.btn_hint.handle(event):
                self.show_solution = not self.show_solution

            if self.show_solution and event.type == pygame.MOUSEBUTTONDOWN:
                self.show_solution = False

            # Drag start
            if event.type == pygame.MOUSEBUTTONDOWN and not self.show_solution:
                mx, my = event.pos
                for i, p in enumerate(self.pieces):
                    if p.is_placed:
                        # pick up from grid
                        wc = p.world_cells()
                        for (r, c) in wc:
                            rx = self.ox + c * CELL
                            ry = self.oy + r * CELL
                            if rx <= mx < rx+CELL and ry <= my < ry+CELL:
                                p.is_placed = False
                                p.dragging = True
                                p.drag_screen = (mx, my)
                                self.drag_offset = (mx - (self.ox + p.grid_pos[0]*CELL),
                                                    my - (self.oy + p.grid_pos[1]*CELL))
                                self.dragging_piece = i
                                break
                    else:
                        # pick up from tray
                        if i < len(self.tray_pos):
                            tx, ty = self.tray_pos[i]
                            min_r, min_c, max_r, max_c = p.bounding_box()
                            hw = (max_c - min_c + 1) * CELL // 2
                            hh = (max_r - min_r + 1) * CELL // 2
                            if abs(mx - tx) < hw + 10 and abs(my - ty) < hh + 10:
                                p.dragging = True
                                p.drag_screen = (mx, my)
                                self.drag_offset = (mx - (tx - hw),
                                                    my - (ty - hh))
                                self.dragging_piece = i
                                break

            # Drag motion
            if event.type == pygame.MOUSEMOTION and self.dragging_piece is not None:
                p = self.pieces[self.dragging_piece]
                p.drag_screen = event.pos

            # Drag end — snap to grid
            if event.type == pygame.MOUSEBUTTONUP and self.dragging_piece is not None:
                p = self.pieces[self.dragging_piece]
                mx, my = event.pos
                piece_left = mx - self.drag_offset[0]
                piece_top = my - self.drag_offset[1]
                gc = round((piece_left - self.ox) / CELL)
                gr = round((piece_top - self.oy) / CELL)

                # clamp so piece stays in grid
                min_r, min_c, max_r, max_c = p.bounding_box()
                gc = max(0, min(gc, self.grid_size - (max_c - min_c + 1)))
                gr = max(0, min(gr, self.grid_size - (max_r - min_r + 1)))

                # Check if the piece overlaps the grid before snapping into place.
                gw = self.grid_size * CELL
                gh = self.grid_size * CELL
                piece_right = piece_left + (max_c - min_c + 1) * CELL
                piece_bottom = piece_top + (max_r - min_r + 1) * CELL
                overlaps_grid = (
                    piece_right > self.ox and
                    piece_left < self.ox + gw and
                    piece_bottom > self.oy and
                    piece_top < self.oy + gh
                )
                if overlaps_grid:
                    p.grid_pos = (gc, gr)
                    p.is_placed = True
                    self.moves += 1
                else:
                    p.is_placed = False

                p.dragging = False
                self.dragging_piece = None

                if not self.solved:
                    self.solved = self.check_solved()

    # ── Draw ──────────────────────────────────────────────────────────────────
    def draw(self):
        self.screen.fill(BG)

        # ── Top bar ──
        draw_text(self.screen, f"LEVEL  {self.current_level:3d} / 100",
                  SCREEN_W//2, 18, self.font_lg, color=BLACK, center=True)
        diff_label = ["EASY","EASY","MEDIUM","MEDIUM","HARD","HARD","HARD","EXPERT","EXPERT","EXPERT","MASTER"][
            min(10, self.current_level // 10)]
        diff_color = [(80,180,80),(80,180,80),(200,160,20),(200,160,20),
                      (220,80,40),(220,80,40),(220,80,40),(180,30,30),(180,30,30),(180,30,30),(120,0,120)][
            min(10, self.current_level // 10)]
        draw_text(self.screen, diff_label, SCREEN_W//2, 50, self.font_sm,
                  color=diff_color, center=True)

        # ── Preview ──
        label = self.font_sm.render("TARGET", True, GREY_MD)
        self.screen.blit(label, (self.prev_ox + PREVIEW_SIZE//2 - label.get_width()//2,
                                  self.prev_oy - 18))
        draw_preview(self.screen, self.target, self.prev_ox, self.prev_oy, PREVIEW_SIZE)

        # ── Play grid ──
        current_grid = compute_grid(self.pieces, self.grid_size)
        draw_grid(self.screen, current_grid, self.ox, self.oy, CELL)

        # ── Grid label ──
        label2 = self.font_sm.render("PLAY AREA  (drag pieces here)", True, GREY_MD)
        self.screen.blit(label2, (self.ox, self.oy - 20))

        # ── Tray pieces ──
        tray_label = self.font_sm.render("PIECES", True, GREY_MD)
        self.screen.blit(tray_label, (SCREEN_W//2 - tray_label.get_width()//2,
                                       self.oy + self.grid_size*CELL + 8))

        for i, p in enumerate(self.pieces):
            if not p.is_placed and not p.dragging:
                if i < len(self.tray_pos):
                    tx, ty = self.tray_pos[i]
                    selected = (self.dragging_piece == i)
                    draw_tray_piece(self.screen, p, tx, ty, CELL, selected)
                    num = self.font_sm.render(str(i+1), True, GREY_MD)
                    self.screen.blit(num, (tx - 5, ty + 30))
            elif p.is_placed and not p.dragging:
                sx = self.ox + p.grid_pos[0] * CELL
                sy = self.oy + p.grid_pos[1] * CELL
                # draw outline only (piece already XOR-ed into grid)
                for (dr, dc) in p.cells:
                    r = pygame.Rect(sx + dc*CELL + 1, sy + dr*CELL + 1, CELL-2, CELL-2)
                    pygame.draw.rect(self.screen, HIGHLIGHT, r, 1)

        # ── Dragging ghost ──
        if self.dragging_piece is not None:
            p = self.pieces[self.dragging_piece]
            if p.dragging:
                mx, my = p.drag_screen
                min_r, min_c, max_r, max_c = p.bounding_box()
                sx = mx - self.drag_offset[0]
                sy = my - self.drag_offset[1]
                draw_piece_at_screen(self.screen, p, sx, sy, CELL,
                                     color=ACCENT, alpha=180)

        # ── Moves counter ──
        draw_text(self.screen, f"Moves: {self.moves}", 20, SCREEN_H//2,
                  self.font_sm, color=GREY_MD)

        # ── Buttons ──
        self.btn_prev.draw(self.screen)
        self.btn_next.draw(self.screen)
        self.btn_reset.draw(self.screen)
        self.btn_hint.draw(self.screen)

        # ── Keyboard hints ──
        hints = "R: reset  │  S: solution  │  ◀▶: level  │  ESC: quit"
        h = self.font_sm.render(hints, True, GREY_MD)
        self.screen.blit(h, (SCREEN_W//2 - h.get_width()//2, SCREEN_H - 22))

        # ── Solved banner ──
        if self.solved:
            banner = self.font_lg.render("✓  PUZZLE SOLVED!", True, WHITE)
            bw = banner.get_width() + 40
            bh = banner.get_height() + 20
            bx = SCREEN_W//2 - bw//2
            by = SCREEN_H//2 - bh//2
            s = pygame.Surface((bw, bh), pygame.SRCALPHA)
            s.fill((30, 160, 60, 230))
            self.screen.blit(s, (bx, by))
            self.screen.blit(banner, (bx+20, by+10))
            sub = self.font_sm.render("Press ▶ or RIGHT ARROW for next level", True, WHITE)
            self.screen.blit(sub, (SCREEN_W//2 - sub.get_width()//2, by+bh+8))

        # ── Solution overlay ──
        if self.show_solution:
            draw_solution_overlay(self.screen, self.level_data, self.ox, self.oy,
                                  CELL, self.font_sm)

        pygame.display.flip()

    # ── Main loop ─────────────────────────────────────────────────────────────
    def run(self):
        print("=" * 55)
        print("  XOR MONOCHROME PUZZLE")
        print("=" * 55)
        print("  Drag black pieces onto the play grid.")
        print("  Overlapping pieces XOR: black+black=white.")
        print("  Match the target pattern to solve!")
        print()
        print("  Controls:")
        print("    Mouse drag  — move pieces")
        print("    R           — reset level")
        print("    S           — show/hide solution")
        print("    ◀ / ▶       — previous / next level")
        print("    ESC         — quit")
        print("=" * 55)

        while True:
            dt = self.clock.tick(FPS) / 1000.0
            if not self.solved:
                self.elapsed += dt
            self.handle_events()
            self.draw()


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="XOR Monochrome Puzzle Game")
    parser.add_argument("--level", type=int, default=1,
                        help="Starting level (0-100, default 1)")
    parser.add_argument("--print-solution", type=int, default=None,
                        help="Print solution for a given level and exit")
    args = parser.parse_args()

    if args.print_solution is not None:
        lvl = args.print_solution
        data = generate_level(lvl)
        print(f"\nLevel {lvl} Solution")
        print(f"Grid size : {data['grid_size']}x{data['grid_size']}")
        print(f"Pieces    : {data['num_pieces']}")
        print()
        print("Target grid (1=black):")
        for row in data["target"]:
            print("  " + " ".join("█" if v else "·" for v in row))
        print()
        print("Piece placements (col, row from top-left = 0,0):")
        for i, (gc, gr) in enumerate(data["solution"]):
            p = data["pieces"][i]
            min_r, min_c, max_r, max_c = p.bounding_box()
            print(f"  Piece {i+1}: place at col={gc}, row={gr}  "
                  f"(size {max_c-min_c+1}×{max_r-min_r+1})")
        sys.exit(0)

    g = Game()
    g.current_level = max(0, min(100, args.level))
    g.load_level(g.current_level)
    g.run()
