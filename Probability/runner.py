import pygame
import sys
import time
import os
from minesweeper import Minesweeper, MinesweeperAI

# Settings
HEIGHT = 9
WIDTH = 9
MINES = 10
CELL_SIZE = 40
MARGIN = 5
WINDOW_WIDTH = WIDTH * (CELL_SIZE + MARGIN) + MARGIN
WINDOW_HEIGHT = HEIGHT * (CELL_SIZE + MARGIN) + MARGIN

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (180, 180, 180)
RED = (255, 0, 0)
GREEN = (0, 255, 0)

# Initialize pygame
pygame.init()
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Minesweeper AI - Probabilistic")
font = pygame.font.SysFont("Arial", 20)

game = Minesweeper(height=HEIGHT, width=WIDTH, mines=MINES)
ai = MinesweeperAI(height=HEIGHT, width=WIDTH)
revealed = set()
flags = set()
lost = False
autoplay = True
autoplaySpeed = 0.1
mine_detonated = None

def draw_board():
    screen.fill(BLACK)
    for i in range(HEIGHT):
        for j in range(WIDTH):
            x = j * (CELL_SIZE + MARGIN) + MARGIN
            y = i * (CELL_SIZE + MARGIN) + MARGIN
            rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)
            cell = (i, j)

            if cell in revealed:
                pygame.draw.rect(screen, GRAY, rect)
                count = game.nearby_mines(cell)
                if count > 0:
                    text = font.render(str(count), True, BLACK)
                    screen.blit(text, (x + 12, y + 10))
            elif cell in flags:
                pygame.draw.rect(screen, GREEN, rect)
            elif lost and game.is_mine(cell):
                color = RED if cell == mine_detonated else BLACK
                pygame.draw.rect(screen, color, rect)
            else:
                pygame.draw.rect(screen, WHITE, rect)
    
    pygame.display.flip()

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    if lost or (game.mines_initialized and len(revealed) == (HEIGHT * WIDTH - MINES)):
        draw_board()
        continue

    if autoplay:
        move = ai.next_move()

        if move:
            if not game.mines_initialized:
                game.place_mines(move)
                game.mines_initialized = True

            if game.is_mine(move):
                lost = True
                mine_detonated = move
            else:
                count = game.nearby_mines(move)
                if count == 0:
                    queue = [move]
                    while queue:
                        current = queue.pop(0)
                        if current in revealed:
                            continue
                        
                        revealed.add(current)
                        ai.add_knowledge(current, game.nearby_mines(current))
                        
                        if game.nearby_mines(current) == 0:
                            for ni in range(current[0] - 1, current[0] + 2):
                                for nj in range(current[1] - 1, current[1] + 2):
                                    neighbor = (ni, nj)
                                    if (0 <= ni < game.height and 0 <= nj < game.width and neighbor not in revealed and neighbor not in flags):
                                        queue.append(neighbor)
                else:
                    revealed.add(move)
                    ai.add_knowledge(move, count)

        else:
            print("Không còn nước đi nào.")
            autoplay = False

        draw_board()
        time.sleep(autoplaySpeed)