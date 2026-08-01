import pygame

from constants import BLACK, WHITE


def draw_text(surf, text, x, y, font, color=BLACK, center=False):
    img = font.render(text, True, color)
    if center:
        x -= img.get_width() // 2
    surf.blit(img, (x, y))


class Button:
    def __init__(self, rect, label, font, color=BLACK, text_color=WHITE):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.font = font
        self.color = color
        self.text_color = text_color
        self.hovered = False

    def draw(self, surf):
        color = tuple(min(255, v + 30) for v in self.color) if self.hovered else self.color
        pygame.draw.rect(surf, color, self.rect, border_radius=6)
        img = self.font.render(self.label, True, self.text_color)
        surf.blit(
            img,
            (self.rect.centerx - img.get_width() // 2, self.rect.centery - img.get_height() // 2),
        )

    def handle(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos):
            return True
        return False
