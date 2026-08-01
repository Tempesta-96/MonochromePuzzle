import pygame

from constants import ACCENT, BASE_SCREEN_W, BG, BLACK, GREY_LT, GREY_MD, HIGHLIGHT, SHADOW, WHITE


def draw_grid(surf, grid, ox, oy, cell, show_dots=True):
    rows = len(grid)
    cols = len(grid[0]) if rows else 0
    pygame.draw.rect(surf, SHADOW, (ox + 4, oy + 4, cols * cell, rows * cell), border_radius=4)
    pygame.draw.rect(surf, WHITE, (ox, oy, cols * cell, rows * cell), border_radius=4)
    for r in range(rows):
        for c in range(cols):
            if grid[r][c]:
                pygame.draw.rect(surf, BLACK, (ox + c * cell, oy + r * cell, cell, cell))
    if show_dots:
        for r in range(rows + 1):
            for c in range(cols + 1):
                pygame.draw.circle(surf, GREY_LT, (ox + c * cell, oy + r * cell), 2)
    pygame.draw.rect(surf, GREY_MD, (ox, oy, cols * cell, rows * cell), 2, border_radius=4)


def draw_piece_at_screen(surf, piece, sx, sy, cell, color=BLACK, alpha=255):
    for dr, dc in piece.cells:
        rect = pygame.Rect(sx + dc * cell, sy + dr * cell, cell, cell)
        if alpha < 255:
            overlay = pygame.Surface((cell, cell), pygame.SRCALPHA)
            overlay.fill((*color, alpha))
            surf.blit(overlay, rect.topleft)
        else:
            pygame.draw.rect(surf, color, rect)


def draw_tray_piece(surf, piece, cx, cy, cell, selected=False):
    min_r, min_c, max_r, max_c = piece.bounding_box()
    h = (max_r - min_r + 1) * cell
    w = (max_c - min_c + 1) * cell
    sx = cx - w // 2 - min_c * cell
    sy = cy - h // 2 - min_r * cell
    color = HIGHLIGHT if selected else BLACK
    draw_piece_at_screen(surf, piece, sx, sy, cell, color=color)


def screen_to_grid(sx, sy, ox, oy, cell):
    return (sx - ox) // cell, (sy - oy) // cell


def grid_to_screen(gc, gr, ox, oy, cell):
    return ox + gc * cell, oy + gr * cell


def grids_match(a, b):
    if len(a) != len(b):
        return False
    for ra, rb in zip(a, b):
        if ra != rb:
            return False
    return True


def tray_positions(pieces, cell: int, top_y: int, left_bound: int = 0, right_bound: int = BASE_SCREEN_W):
    if not pieces:
        return []

    horizontal_gap = 24
    vertical_gap = 28
    side_margin = 36
    available_width = right_bound - left_bound
    max_row_width = max(120, available_width - side_margin * 2)

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
        x = left_bound + (available_width - row_width) // 2
        for index, piece_w, piece_h in row:
            positions[index] = (x + piece_w // 2, y + row_height // 2)
            x += piece_w + horizontal_gap
        y += row_height + vertical_gap

    return positions


def tray_bottom(pieces, positions, cell: int):
    bottom = 0
    for piece, (_, cy) in zip(pieces, positions):
        min_r, min_c, max_r, max_c = piece.bounding_box()
        piece_h = (max_r - min_r + 1) * cell
        bottom = max(bottom, cy + piece_h // 2)
    return bottom


def draw_preview(surf, target, ox, oy, size):
    grid_size = len(target)
    cell = size // grid_size
    actual_w = cell * grid_size
    actual_h = cell * grid_size
    px = ox + (size - actual_w) // 2
    py = oy + (size - actual_h) // 2
    pygame.draw.rect(surf, WHITE, (px, py, actual_w, actual_h))
    for r in range(grid_size):
        for c in range(grid_size):
            if target[r][c]:
                pygame.draw.rect(surf, BLACK, (px + c * cell, py + r * cell, cell, cell))
    pygame.draw.rect(surf, GREY_MD, (px, py, actual_w, actual_h), 2)


def draw_solution_overlay(surf, level_data, ox, oy, cell, font_sm):
    screen_w, screen_h = surf.get_size()
    grid_size = level_data["grid_size"]
    pieces = level_data["pieces"]
    solution = level_data["solution"]
    colors = [
        (220, 60, 40),
        (40, 120, 220),
        (40, 180, 80),
        (200, 140, 20),
        (140, 40, 200),
        (20, 180, 180),
        (220, 100, 180),
        (100, 100, 100),
    ]

    overlay = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    surf.blit(overlay, (0, 0))

    panel_w, panel_h = grid_size * cell + 160, grid_size * cell + 100
    px = (screen_w - panel_w) // 2
    py = (screen_h - panel_h) // 2
    pygame.draw.rect(surf, BG, (px, py, panel_w, panel_h), border_radius=10)
    pygame.draw.rect(surf, GREY_MD, (px, py, panel_w, panel_h), 2, border_radius=10)

    title = font_sm.render("SOLUTION", True, ACCENT)
    surf.blit(title, (px + panel_w // 2 - title.get_width() // 2, py + 12))

    gx = px + 80
    gy = py + 50
    pygame.draw.rect(surf, WHITE, (gx, gy, grid_size * cell, grid_size * cell))
    for i, (piece, (gc, gr)) in enumerate(zip(pieces, solution)):
        color = colors[i % len(colors)]
        for dr, dc in piece.cells:
            r, c = gr + dr, gc + dc
            if 0 <= r < grid_size and 0 <= c < grid_size:
                overlay_cell = pygame.Surface((cell, cell), pygame.SRCALPHA)
                overlay_cell.fill((*color, 140))
                surf.blit(overlay_cell, (gx + c * cell, gy + r * cell))
        label = font_sm.render(f"P{i+1}", True, color)
        surf.blit(label, (px + 10, gy + gr * cell + dr * cell // 2))

    pygame.draw.rect(surf, GREY_MD, (gx, gy, grid_size * cell, grid_size * cell), 2)
    hint = font_sm.render("Press S or click elsewhere to close", True, GREY_MD)
    surf.blit(hint, (px + panel_w // 2 - hint.get_width() // 2, py + panel_h - 28))
