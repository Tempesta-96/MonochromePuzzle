import sys

import pygame

from constants import (
    ACCENT,
    BASE_SCREEN_H,
    BASE_SCREEN_W,
    BG,
    BLACK,
    CELL,
    FPS,
    GREY_LT,
    GREY_MD,
    HIGHLIGHT,
    PREVIEW_SIZE,
    TARGET_Y,
    WHITE,
)
from generation import compute_grid, generate_level
from models import Piece
from rendering import (
    draw_grid,
    draw_piece_at_screen,
    draw_preview,
    draw_solution_overlay,
    draw_tray_piece,
    grids_match,
    tray_bottom,
    tray_positions,
)
from ui import Button, draw_text


class Game:
    def __init__(self):
        pygame.init()
        self.screen_w = BASE_SCREEN_W
        self.screen_h = BASE_SCREEN_H
        self.screen = pygame.display.set_mode((self.screen_w, self.screen_h))
        pygame.display.set_caption("XOR Monochrome Puzzle")
        self.clock = pygame.time.Clock()

        self.font_lg = pygame.font.SysFont("Georgia", 28, bold=True)
        self.font_md = pygame.font.SysFont("Georgia", 20)
        self.font_sm = pygame.font.SysFont("Georgia", 15)
        self.font_num = pygame.font.SysFont("Courier New", 24, bold=True)

        self.current_level = 1
        self.show_solution = False
        self.show_level_menu = False
        self.show_first_hint = False
        self.solved = False
        self.elapsed = 0.0
        self.moves = 0

        self.load_level(self.current_level)

        bw, bh = 110, 34
        top_btn_y = 20
        top_btn_gap = 18
        group_w = bw * 3 + top_btn_gap * 2
        group_x = (self.screen_w - group_w) // 2
        self.btn_prev = Button((group_x, top_btn_y, bw, bh), "◀ PREV", self.font_sm, BLACK)
        self.btn_level = Button((group_x + bw + top_btn_gap, top_btn_y, bw, bh), "LEVELS", self.font_sm, (70, 70, 70))
        self.btn_next = Button((group_x + (bw + top_btn_gap) * 2, top_btn_y, bw, bh), "NEXT ▶", self.font_sm, BLACK)
        self.btn_reset = Button((20, self.screen_h - 60, bw, bh), "↺ RESET", self.font_sm, (80, 80, 80))
        self.btn_hint = Button((self.screen_w - 130, self.screen_h - 60, bw, bh), "💡 HINT", self.font_sm, (60, 130, 60))

        self.dragging_piece = None
        self.drag_offset = (0, 0)

    def calculate_screen_width(self, pieces, cell: int):
        horizontal_gap = 24
        side_margin = 36
        tray_width = 0
        for i, piece in enumerate(pieces):
            min_r, min_c, max_r, max_c = piece.bounding_box()
            piece_w = (max_c - min_c + 1) * cell
            tray_width += piece_w
            if i:
                tray_width += horizontal_gap
        tray_width += side_margin * 2
        return max(BASE_SCREEN_W, tray_width + 40)

    def update_top_ui(self):
        bw = self.btn_prev.rect.width
        top_btn_y = self.btn_prev.rect.y
        top_btn_gap = 18
        group_w = bw * 3 + top_btn_gap * 2
        group_x = (self.screen_w - group_w) // 2
        self.btn_prev.rect.topleft = (group_x, top_btn_y)
        self.btn_level.rect.topleft = (group_x + bw + top_btn_gap, top_btn_y)
        self.btn_next.rect.topleft = (group_x + (bw + top_btn_gap) * 2, top_btn_y)

    def update_bottom_ui(self):
        self.btn_reset.rect.topleft = (20, self.screen_h - 60)
        self.btn_hint.rect.topleft = (self.screen_w - 130, self.screen_h - 60)

    def content_center_x(self):
        return self.screen_w // 2

    def level_menu_rect(self):
        width = max(520, self.screen_w - 240)
        return pygame.Rect((self.screen_w - width) // 2, 90, width, min(500, self.screen_h - 160))

    def level_menu_item_rect(self, level: int):
        panel = self.level_menu_rect()
        cols = 10
        rows = 11
        top_pad = 58
        side_pad = 18
        bottom_pad = 18
        row_gap = 10
        col_gap = 10
        cell_w = (panel.width - side_pad * 2 - col_gap * (cols - 1)) // cols
        cell_h = (panel.height - top_pad - bottom_pad - row_gap * (rows - 1)) // rows
        col = level % cols
        row = level // cols
        x = panel.x + side_pad + col * (cell_w + col_gap)
        y = panel.y + top_pad + row * (cell_h + row_gap)
        return pygame.Rect(x, y, cell_w, cell_h)

    def level_at_menu_pos(self, pos):
        if not self.level_menu_rect().collidepoint(pos):
            return None
        for level in range(101):
            if self.level_menu_item_rect(level).collidepoint(pos):
                return level
        return None

    def next_hint_index(self):
        for i, (piece, target_pos) in enumerate(zip(self.pieces, self.solution)):
            if not piece.is_placed or piece.grid_pos != target_pos:
                return i
        return None

    def load_level(self, level: int):
        self.current_level = max(0, min(100, level))
        data = generate_level(self.current_level)
        self.level_data = data
        self.target = data["target"]
        self.grid_size = data["grid_size"]
        self.solution = data["solution"]
        self.pieces = [Piece(cells=list(piece.cells), grid_pos=(0, 0)) for piece in data["pieces"]]

        self.show_solution = False
        self.show_first_hint = False
        self.solved = False
        self.elapsed = 0.0
        self.moves = 0

        self.screen_w = self.calculate_screen_width(self.pieces, CELL)
        content_center = self.content_center_x()
        self.ox = content_center - (self.grid_size * CELL) // 2
        self.oy = TARGET_Y + PREVIEW_SIZE + 50
        self.prev_ox = content_center - PREVIEW_SIZE // 2
        self.prev_oy = TARGET_Y

        tray_top = self.oy + self.grid_size * CELL + 30
        self.tray_pos = tray_positions(self.pieces, CELL, tray_top, 0, self.screen_w)
        tray_end = tray_bottom(self.pieces, self.tray_pos, CELL)

        self.screen_h = max(BASE_SCREEN_H, tray_end + 90)
        self.screen = pygame.display.set_mode((self.screen_w, self.screen_h))
        if hasattr(self, "btn_prev"):
            self.update_top_ui()
        if hasattr(self, "btn_reset"):
            self.update_bottom_ui()

    def check_solved(self):
        current = compute_grid(self.pieces, self.grid_size)
        return grids_match(current, self.target)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.show_level_menu:
                        self.show_level_menu = False
                    elif self.show_solution:
                        self.show_solution = False
                    else:
                        pygame.quit()
                        sys.exit()
                if event.key == pygame.K_s:
                    self.show_solution = not self.show_solution
                    if self.show_solution:
                        self.show_first_hint = False
                if event.key == pygame.K_r:
                    self.load_level(self.current_level)
                if event.key == pygame.K_RIGHT:
                    self.load_level(self.current_level + 1)
                if event.key == pygame.K_LEFT:
                    self.load_level(self.current_level - 1)

            if self.btn_prev.handle(event):
                self.load_level(self.current_level - 1)
            if self.btn_next.handle(event):
                self.load_level(self.current_level + 1)
            if self.btn_level.handle(event):
                self.show_level_menu = not self.show_level_menu
                if self.show_level_menu:
                    self.show_solution = False
                    self.show_first_hint = False
                continue
            if self.btn_reset.handle(event):
                self.load_level(self.current_level)
            if self.btn_hint.handle(event):
                self.show_first_hint = not self.show_first_hint
                if self.show_first_hint:
                    self.show_solution = False
                continue

            if self.show_level_menu and event.type == pygame.MOUSEBUTTONDOWN:
                level = self.level_at_menu_pos(event.pos)
                if level is not None:
                    self.load_level(level)
                    self.show_level_menu = False
                elif not self.level_menu_rect().collidepoint(event.pos):
                    self.show_level_menu = False
                continue

            if self.show_solution and event.type == pygame.MOUSEBUTTONDOWN:
                self.show_solution = False

            if self.show_first_hint and event.type == pygame.MOUSEBUTTONDOWN:
                hint_cells = set()
                hint_index = self.next_hint_index()
                if hint_index is not None:
                    hint_piece = self.pieces[hint_index]
                    gc, gr = self.solution[hint_index]
                    for dr, dc in hint_piece.cells:
                        hint_cells.add((gr + dr, gc + dc))
                if not any(
                    self.ox + c * CELL <= event.pos[0] < self.ox + (c + 1) * CELL
                    and self.oy + r * CELL <= event.pos[1] < self.oy + (r + 1) * CELL
                    for r, c in hint_cells
                ):
                    self.show_first_hint = False

            if event.type == pygame.MOUSEBUTTONDOWN and not self.show_solution and not self.show_level_menu:
                mx, my = event.pos
                picked_piece = False
                for i in range(len(self.pieces) - 1, -1, -1):
                    piece = self.pieces[i]
                    if piece.is_placed:
                        for r, c in piece.world_cells():
                            rx = self.ox + c * CELL
                            ry = self.oy + r * CELL
                            if rx <= mx < rx + CELL and ry <= my < ry + CELL:
                                piece.is_placed = False
                                piece.dragging = True
                                piece.drag_screen = (mx, my)
                                self.drag_offset = (
                                    mx - (self.ox + piece.grid_pos[0] * CELL),
                                    my - (self.oy + piece.grid_pos[1] * CELL),
                                )
                                self.dragging_piece = i
                                picked_piece = True
                                break
                    else:
                        if i < len(self.tray_pos):
                            tx, ty = self.tray_pos[i]
                            min_r, min_c, max_r, max_c = piece.bounding_box()
                            hw = (max_c - min_c + 1) * CELL // 2
                            hh = (max_r - min_r + 1) * CELL // 2
                            if abs(mx - tx) < hw + 10 and abs(my - ty) < hh + 10:
                                piece.dragging = True
                                piece.drag_screen = (mx, my)
                                self.drag_offset = (mx - (tx - hw), my - (ty - hh))
                                self.dragging_piece = i
                                picked_piece = True
                                break
                    if picked_piece:
                        break

            if event.type == pygame.MOUSEMOTION and self.dragging_piece is not None:
                self.pieces[self.dragging_piece].drag_screen = event.pos

            if event.type == pygame.MOUSEBUTTONUP and self.dragging_piece is not None:
                piece = self.pieces[self.dragging_piece]
                mx, my = event.pos
                piece_left = mx - self.drag_offset[0]
                piece_top = my - self.drag_offset[1]
                gc = round((piece_left - self.ox) / CELL)
                gr = round((piece_top - self.oy) / CELL)

                min_r, min_c, max_r, max_c = piece.bounding_box()
                gc = max(0, min(gc, self.grid_size - (max_c - min_c + 1)))
                gr = max(0, min(gr, self.grid_size - (max_r - min_r + 1)))

                gw = self.grid_size * CELL
                gh = self.grid_size * CELL
                piece_right = piece_left + (max_c - min_c + 1) * CELL
                piece_bottom = piece_top + (max_r - min_r + 1) * CELL
                overlaps_grid = (
                    piece_right > self.ox
                    and piece_left < self.ox + gw
                    and piece_bottom > self.oy
                    and piece_top < self.oy + gh
                )
                if overlaps_grid:
                    piece.grid_pos = (gc, gr)
                    piece.is_placed = True
                    self.moves += 1
                else:
                    piece.is_placed = False

                piece.dragging = False
                self.dragging_piece = None

                if not self.solved:
                    self.solved = self.check_solved()

    def draw(self):
        self.screen.fill(BG)
        content_center_x = self.content_center_x()

        draw_text(self.screen, f"LEVEL  {self.current_level:3d} / 100", content_center_x, 62, self.font_lg, color=BLACK, center=True)
        diff_label = ["EASY", "EASY", "MEDIUM", "MEDIUM", "HARD", "HARD", "HARD", "EXPERT", "EXPERT", "EXPERT", "MASTER"][min(10, self.current_level // 10)]
        diff_color = [
            (80, 180, 80),
            (80, 180, 80),
            (200, 160, 20),
            (200, 160, 20),
            (220, 80, 40),
            (220, 80, 40),
            (220, 80, 40),
            (180, 30, 30),
            (180, 30, 30),
            (180, 30, 30),
            (120, 0, 120),
        ][min(10, self.current_level // 10)]
        draw_text(self.screen, diff_label, content_center_x, 94, self.font_sm, color=diff_color, center=True)

        label = self.font_sm.render("TARGET", True, GREY_MD)
        self.screen.blit(label, (self.prev_ox + PREVIEW_SIZE // 2 - label.get_width() // 2, self.prev_oy - 18))
        draw_preview(self.screen, self.target, self.prev_ox, self.prev_oy, PREVIEW_SIZE)

        current_grid = compute_grid(self.pieces, self.grid_size)
        draw_grid(self.screen, current_grid, self.ox, self.oy, CELL)
        hint_index = self.next_hint_index() if self.show_first_hint else None
        if hint_index is not None:
            hint_piece = self.pieces[hint_index]
            hint_gc, hint_gr = self.solution[hint_index]
            for dr, dc in hint_piece.cells:
                hint_rect = pygame.Rect(
                    self.ox + (hint_gc + dc) * CELL + 3,
                    self.oy + (hint_gr + dr) * CELL + 3,
                    CELL - 6,
                    CELL - 6,
                )
                pygame.draw.rect(self.screen, ACCENT, hint_rect, 3, border_radius=6)

        label2 = self.font_sm.render("PLAY AREA  (drag pieces here)", True, GREY_MD)
        self.screen.blit(label2, (self.ox, self.oy - 20))

        tray_label = self.font_sm.render("PIECES", True, GREY_MD)
        self.screen.blit(tray_label, (content_center_x - tray_label.get_width() // 2, self.oy + self.grid_size * CELL + 8))

        for i, piece in enumerate(self.pieces):
            if not piece.is_placed and not piece.dragging:
                if i < len(self.tray_pos):
                    tx, ty = self.tray_pos[i]
                    selected = (self.dragging_piece == i) or (hint_index is not None and i == hint_index)
                    draw_tray_piece(self.screen, piece, tx, ty, CELL, selected)
                    num = self.font_sm.render(str(i + 1), True, GREY_MD)
                    self.screen.blit(num, (tx - 5, ty + 30))
            elif piece.is_placed and not piece.dragging:
                sx = self.ox + piece.grid_pos[0] * CELL
                sy = self.oy + piece.grid_pos[1] * CELL
                for dr, dc in piece.cells:
                    rect = pygame.Rect(sx + dc * CELL + 1, sy + dr * CELL + 1, CELL - 2, CELL - 2)
                    pygame.draw.rect(self.screen, HIGHLIGHT, rect, 1)

        if self.dragging_piece is not None:
            piece = self.pieces[self.dragging_piece]
            if piece.dragging:
                mx, my = piece.drag_screen
                sx = mx - self.drag_offset[0]
                sy = my - self.drag_offset[1]
                draw_piece_at_screen(self.screen, piece, sx, sy, CELL, color=ACCENT, alpha=180)

        draw_text(self.screen, f"Moves: {self.moves}", 20, self.screen_h // 2, self.font_sm, color=GREY_MD)

        self.btn_prev.draw(self.screen)
        self.btn_next.draw(self.screen)
        self.btn_level.draw(self.screen)
        self.btn_reset.draw(self.screen)
        self.btn_hint.draw(self.screen)

        hints = "R: reset  │  S: solution  │  ◀▶: level  │  ESC: quit"
        hint_text = self.font_sm.render(hints, True, GREY_MD)
        self.screen.blit(hint_text, (content_center_x - hint_text.get_width() // 2, self.screen_h - 22))

        if self.solved:
            banner = self.font_lg.render("✓  PUZZLE SOLVED!", True, WHITE)
            bw = banner.get_width() + 40
            bh = banner.get_height() + 20
            bx = self.screen_w // 2 - bw // 2
            by = self.screen_h // 2 - bh // 2
            overlay = pygame.Surface((bw, bh), pygame.SRCALPHA)
            overlay.fill((30, 160, 60, 230))
            self.screen.blit(overlay, (bx, by))
            self.screen.blit(banner, (bx + 20, by + 10))
            sub = self.font_sm.render("Press ▶ or RIGHT ARROW for next level", True, WHITE)
            self.screen.blit(sub, (content_center_x - sub.get_width() // 2, by + bh + 8))

        if self.show_solution:
            draw_solution_overlay(self.screen, self.level_data, self.ox, self.oy, CELL, self.font_sm)

        if self.show_level_menu:
            overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            self.screen.blit(overlay, (0, 0))

            panel = self.level_menu_rect()
            pygame.draw.rect(self.screen, BG, panel, border_radius=12)
            pygame.draw.rect(self.screen, GREY_MD, panel, 2, border_radius=12)

            title = self.font_md.render("Select Level", True, BLACK)
            subtitle = self.font_sm.render("Click a level to jump there. Click outside to close.", True, GREY_MD)
            self.screen.blit(title, (panel.centerx - title.get_width() // 2, panel.y + 14))
            self.screen.blit(subtitle, (panel.centerx - subtitle.get_width() // 2, panel.y + 36))

            for level in range(101):
                item_rect = self.level_menu_item_rect(level)
                selected = level == self.current_level
                color = BLACK if selected else (248, 246, 241)
                text_color = WHITE if selected else GREY_MD
                pygame.draw.rect(self.screen, color, item_rect, border_radius=8)
                pygame.draw.rect(self.screen, GREY_LT, item_rect, 1, border_radius=8)
                label = self.font_sm.render(f"{level:3d}", True, text_color)
                self.screen.blit(label, (item_rect.centerx - label.get_width() // 2, item_rect.centery - label.get_height() // 2))

        pygame.display.flip()

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
