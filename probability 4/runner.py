import pygame
import sys
import time
import os
from minesweeper import Minesweeper, MinesweeperAI

# Settings
HEIGHT = 16
WIDTH = 16
MINES = 40
CELL_SIZE = 30
MARGIN = 2 # Increased margin for better spacing
BOARD_PADDING_LEFT = 20
BOARD_PADDING_TOP = 80
WINDOW_WIDTH = 600
WINDOW_HEIGHT = 500

# Colors
BLACK = (0, 0, 0)
GRAY = (192, 192, 192)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)

# Initialize pygame
pygame.init()
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Minesweeper")

# Load assets
def load_assets():
    assets = {}
    base_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(base_dir, 'assets')

    # Load fonts
    try:
        font_path = os.path.join(assets_dir, 'fonts', 'mine-sweeper.ttf')
        assets['font_large'] = pygame.font.Font(font_path, 48)
        assets['font_medium'] = pygame.font.Font(font_path, 24)
        assets['font_small'] = pygame.font.Font(font_path, 18)
    except FileNotFoundError as e:
        print(f"Error loading font: {e}. Using default font.")
        assets['font_large'] = pygame.font.SysFont("Arial", 48)
        assets['font_medium'] = pygame.font.SysFont("Arial", 24)
        assets['font_small'] = pygame.font.SysFont("Arial", 18)

    # Load images
    image_dir = os.path.join(assets_dir, 'images')
    try:
        assets['unrevealed'] = pygame.image.load(os.path.join(image_dir, 'unrevealed.png')).convert()
        assets['flag'] = pygame.image.load(os.path.join(image_dir, 'flag.png')).convert_alpha()
        assets['mine'] = pygame.image.load(os.path.join(image_dir, 'mine.png')).convert()
        assets['mine_exploded'] = pygame.image.load(os.path.join(image_dir, 'mine-red.png')).convert()
        assets['logo_flag'] = pygame.image.load(os.path.join(image_dir, 'flag2.png')).convert_alpha()
        for i in range(9):
            assets['num_' + str(i)] = pygame.image.load(os.path.join(image_dir, f'{i}.png')).convert()
    except FileNotFoundError as e:
        print(f"Error loading image: {e}")
        pygame.quit()
        sys.exit()

    # Scale images
    for key, img in assets.items():
        if key not in ['font_large', 'font_medium', 'font_small']:
            assets[key] = pygame.transform.scale(img, (CELL_SIZE, CELL_SIZE))

    return assets

assets = load_assets()

# Create game and AI agent
game = Minesweeper(height=HEIGHT, width=WIDTH, mines=MINES)
ai = MinesweeperAI(height=HEIGHT, width=WIDTH)

# Game state variables
revealed = set()
flags = set()
lost = False
first_click = True
autoplay = False
autoplay_delay = 0.2
mine_exploded_pos = None
show_inference = False
loop_autoplay = False
autoplay_games = 0
autoplay_wins = 0
autoplay_start_time = None
autoplay_total_time = 0

# Button dimensions and positions
BUTTON_WIDTH = 120
BUTTON_HEIGHT = 30
BUTTON_PADDING = 10
BUTTON_START_X = WINDOW_WIDTH - BUTTON_WIDTH - 20
AUTOPLAY_BUTTON_Y = 100
AI_MOVE_BUTTON_Y = AUTOPLAY_BUTTON_Y + BUTTON_HEIGHT + BUTTON_PADDING
RESET_BUTTON_Y = AI_MOVE_BUTTON_Y + BUTTON_HEIGHT + BUTTON_PADDING
SHOW_INFERENCE_BUTTON_Y = RESET_BUTTON_Y + BUTTON_HEIGHT + 3 * BUTTON_PADDING
LOOP_AUTOPLAY_BUTTON_Y = SHOW_INFERENCE_BUTTON_Y + BUTTON_HEIGHT + BUTTON_PADDING
PLAY_BUTTON_RECT = pygame.Rect(WINDOW_WIDTH // 2 - 100, WINDOW_HEIGHT // 2 + 50, 200, 50)

def draw_text(text, font, color, surface, x, y):
    textobj = font.render(text, 1, color)
    textrect = textobj.get_rect()
    textrect.topleft = (x, y)
    surface.blit(textobj, textrect)
    return textrect

def draw_button(text, rect, color, text_color, surface, font):
    pygame.draw.rect(surface, color, rect)
    text_surface = font.render(text, True, text_color)
    text_rect = text_surface.get_rect(center=rect.center)
    surface.blit(text_surface, text_rect)
    return rect

def draw_board():
    for i in range(HEIGHT):
        for j in range(WIDTH):
            x = BOARD_PADDING_LEFT + j * (CELL_SIZE + MARGIN)
            y = BOARD_PADDING_TOP + i * (CELL_SIZE + MARGIN)
            rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)
            cell = (i, j)

            if cell in revealed:
                pygame.draw.rect(screen, GRAY, rect)
                mines_nearby = game.nearby_mines(cell)
                if mines_nearby > 0:
                    text_image = assets.get(f'num_{mines_nearby}')
                    if text_image:
                        screen.blit(text_image, rect)
            elif cell in flags:
                screen.blit(assets['flag'], rect)
            elif lost and game.is_mine(cell):
                if cell == mine_exploded_pos:
                    screen.blit(assets['mine_exploded'], rect)
                else:
                    screen.blit(assets['mine'], rect)
            else:
                screen.blit(assets['unrevealed'], rect)

def show_instructions():
    screen.fill(BLACK)
    draw_text("MINESWEEPER", assets['font_large'], WHITE, screen, 20, 50)
    screen.blit(pygame.transform.scale(assets['logo_flag'], (30, 30)), (260, 55))
    screen.blit(pygame.transform.scale(assets['logo_flag'], (30, 30)), (180, 55))

    instructions_text = [
        "LEFT-CLICK to reveal a tile",
        "RIGHT-CLICK to flag a mine",
        "The numbers show nearby mines",
        "Reveal all safe tiles to win!"
    ]
    start_y = 150
    for line in instructions_text:
        text_rect = draw_text(line, assets['font_medium'], WHITE, screen, 20, start_y)
        start_y += 40

    draw_button("PLAY GAME", PLAY_BUTTON_RECT, WHITE, BLACK, screen, assets['font_medium'])

def handle_move(move):
    global first_click, lost, mine_exploded_pos
    if first_click:
        game.place_mines(move)
        first_click = False
        
    lost_game, exploded_mine = game.handle_move(move, ai, revealed, flags)
    
    if lost_game:
        lost = True
        mine_exploded_pos = exploded_mine
    
    return lost_game

autoplay_button_rect = pygame.Rect(BUTTON_START_X, AUTOPLAY_BUTTON_Y, BUTTON_WIDTH, BUTTON_HEIGHT)
ai_move_button_rect = pygame.Rect(BUTTON_START_X, AI_MOVE_BUTTON_Y, BUTTON_WIDTH, BUTTON_HEIGHT)
reset_button_rect = pygame.Rect(BUTTON_START_X, RESET_BUTTON_Y, BUTTON_WIDTH, BUTTON_HEIGHT)
show_inference_button_rect = pygame.Rect(BUTTON_START_X, SHOW_INFERENCE_BUTTON_Y, BUTTON_WIDTH, BUTTON_HEIGHT)
loop_autoplay_button_rect = pygame.Rect(BUTTON_START_X, LOOP_AUTOPLAY_BUTTON_Y, BUTTON_WIDTH, BUTTON_HEIGHT)

instructions = True

while True:
    mouse_pos = pygame.mouse.get_pos()
    click = False
    right_click = False
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                click = True
            elif event.button == 3:
                right_click = True

    if instructions:
        show_instructions()
        if click and PLAY_BUTTON_RECT.collidepoint(mouse_pos):
            instructions = False
            game = Minesweeper(height=HEIGHT, width=WIDTH, mines=MINES)
            ai = MinesweeperAI(height=HEIGHT, width=WIDTH)
            revealed.clear()
            flags.clear()
            lost = False
            first_click = True
            mine_exploded_pos = None
            autoplay_games = 0
            autoplay_wins = 0
            autoplay_total_time = 0
            autoplay_start_time = None

        pygame.display.flip()
        continue

    screen.fill(BLACK)
    draw_board()

    # Draw buttons
    autoplay_text = "Stop Autoplay" if autoplay else "Autoplay"
    draw_button(autoplay_text, autoplay_button_rect, WHITE, BLACK, screen, assets['font_small'])
    draw_button("AI Move", ai_move_button_rect, WHITE, BLACK, screen, assets['font_small'])
    draw_button("Reset", reset_button_rect, WHITE, BLACK, screen, assets['font_small'])
    inference_text = "Hide Inference" if show_inference else "Show Inference"
    draw_button(inference_text, show_inference_button_rect, WHITE, BLACK, screen, assets['font_small'])
    loop_autoplay_text = "Stop Loop" if loop_autoplay else "Loop Autoplay"
    draw_button(loop_autoplay_text, loop_autoplay_button_rect, WHITE, BLACK, screen, assets['font_small'])

    # Display game status
    status_text = ""
    if lost:
        status_text = "You Lose :("
    elif game.mines_initialized and len(revealed) == (HEIGHT * WIDTH - MINES):
        status_text = "You Win :D"
    draw_text(status_text, assets['font_medium'], WHITE, screen, BOARD_PADDING_LEFT, 20)

    # Display autoplay statistics
    if autoplay_games > 0:
        avg_speed = autoplay_total_time / autoplay_games if autoplay_games > 0 else 0
        win_rate = (autoplay_wins / autoplay_games) * 100 if autoplay_games > 0 else 0
        draw_text(f"Games: {autoplay_games}", assets['font_small'], WHITE, screen, BOARD_PADDING_LEFT, 50)
        draw_text(f"Wins: {autoplay_wins} ({win_rate:.1f}%)", assets['font_small'], WHITE, screen, BOARD_PADDING_LEFT, 70)
        draw_text(f"Avg Time: {avg_speed:.2f}s", assets['font_small'], WHITE, screen, BOARD_PADDING_LEFT, 90)

    pygame.display.flip()

    if click:
        if autoplay_button_rect.collidepoint(mouse_pos):
            autoplay = not autoplay
            if autoplay and loop_autoplay:
                loop_autoplay = False
            if autoplay and not autoplay_start_time:
                autoplay_start_time = time.time()
        elif ai_move_button_rect.collidepoint(mouse_pos) and not lost and not autoplay:
            move = ai.next_move()
            if move:
                handle_move(move)
        elif reset_button_rect.collidepoint(mouse_pos):
            game = Minesweeper(height=HEIGHT, width=WIDTH, mines=MINES)
            ai = MinesweeperAI(height=HEIGHT, width=WIDTH)
            revealed.clear()
            flags.clear()
            lost = False
            first_click = True
            mine_exploded_pos = None
            autoplay = False
            loop_autoplay = False
            autoplay_games = 0
            autoplay_wins = 0
            autoplay_total_time = 0
            autoplay_start_time = None
        elif show_inference_button_rect.collidepoint(mouse_pos):
            show_inference = not show_inference
        elif loop_autoplay_button_rect.collidepoint(mouse_pos) and not autoplay:
            loop_autoplay = not loop_autoplay
            if loop_autoplay:
                autoplay = True
                if not autoplay_start_time:
                    autoplay_start_time = time.time()
        else:
            col = (mouse_pos[0] - BOARD_PADDING_LEFT) // (CELL_SIZE + MARGIN)
            row = (mouse_pos[1] - BOARD_PADDING_TOP) // (CELL_SIZE + MARGIN)
            if 0 <= row < HEIGHT and 0 <= col < WIDTH and (row, col) not in revealed and (row, col) not in flags:
                handle_move((row, col))

    if right_click:
        col = (mouse_pos[0] - BOARD_PADDING_LEFT) // (CELL_SIZE + MARGIN)
        row = (mouse_pos[1] - BOARD_PADDING_TOP) // (CELL_SIZE + MARGIN)
        if 0 <= row < HEIGHT and 0 <= col < WIDTH and (row, col) not in revealed:
            if (row, col) in flags:
                flags.remove((row, col))
            else:
                flags.add((row, col))

    if autoplay and not lost:
        move = ai.next_move()
        if move:
            if handle_move(move):
                if loop_autoplay:
                    autoplay_games += 1
                    if not lost: autoplay_wins += 1
                    autoplay_total_time += time.time() - autoplay_start_time
                    game = Minesweeper(height=HEIGHT, width=WIDTH, mines=MINES)
                    ai = MinesweeperAI(height=HEIGHT, width=WIDTH)
                    revealed.clear()
                    flags.clear()
                    lost = False
                    first_click = True
                    mine_exploded_pos = None
                    autoplay_start_time = time.time()
                else:
                    autoplay_games += 1
                    if not lost: autoplay_wins += 1
                    autoplay_total_time += time.time() - autoplay_start_time
                    autoplay = False
            time.sleep(autoplay_delay)
        elif autoplay:
            autoplay = False