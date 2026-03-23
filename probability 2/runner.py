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
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

# Initialize pygame
pygame.init()
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Minesweeper AI - Probabilistic")

# Load assets
def load_assets():
    assets = {}
    
    # Path to assets folder (assuming it's in the same directory as runner.py)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(base_dir, 'assets')
    
    # Load fonts
    try:
        font_path = os.path.join(assets_dir, 'fonts', 'mine-sweeper.ttf')
        assets['font'] = pygame.font.Font(font_path, 30)
    except FileNotFoundError:
        print(f"Error: Font file not found at {font_path}. Using default system font.")
        assets['font'] = pygame.font.SysFont("Arial", 30)

    # Load images
    image_dir = os.path.join(assets_dir, 'images')
    
    # Number images 0-8
    for i in range(9):
        try:
            path = os.path.join(image_dir, f'{i}.png')
            assets[f'{i}'] = pygame.image.load(path).convert_alpha()
        except FileNotFoundError:
            print(f"Error: Image file {i}.png not found at {path}.")
            
    # Other images
    try:
        assets['unrevealed'] = pygame.image.load(os.path.join(image_dir, 'unrevealed.png')).convert_alpha()
        assets['flag'] = pygame.image.load(os.path.join(image_dir, 'flag.png')).convert_alpha()
        assets['mine'] = pygame.image.load(os.path.join(image_dir, 'mine.png')).convert_alpha()
        assets['mine-red'] = pygame.image.load(os.path.join(image_dir, 'mine-red.png')).convert_alpha()
        assets['flag2'] = pygame.image.load(os.path.join(image_dir, 'flag2.png')).convert_alpha()
        assets['sprite200'] = pygame.image.load(os.path.join(image_dir, 'sprite200.gif')).convert_alpha()
    except FileNotFoundError as e:
        print(f"Error: Asset file not found: {e}")

    # Scale images
    for key, img in assets.items():
        if key not in ['font']:
            assets[key] = pygame.transform.scale(img, (CELL_SIZE, CELL_SIZE))

    return assets

assets = load_assets()

# Create game and AI instances
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
            cell = (i, j)
            
            # Use images to draw the board
            image = None
            if cell in revealed:
                count = game.nearby_mines(cell)
                image = assets.get(str(count))
            elif cell in flags:
                image = assets.get('flag')
            elif lost and game.is_mine(cell):
                image = assets.get('mine-red') if cell == mine_detonated else assets.get('mine')
            else:
                image = assets.get('unrevealed')
            
            if image:
                screen.blit(image, (x, y))

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