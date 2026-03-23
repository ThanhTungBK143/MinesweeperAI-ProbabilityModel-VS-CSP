import pygame
import sys
import time

from minesweeper import Minesweeper, MinesweeperAI
import os

BASE_DIR = os.path.dirname(__file__)
# Default difficulty
HEIGHT = 9
WIDTH = 9
MINES = 10

# Colors
BLACK = (0, 0, 0)
GRAY = (180, 180, 180)
WHITE = (255, 255, 255)
PINK = (255, 192, 203)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
RED_OVERLAY = (255, 0, 0, 128)
GREEN_OVERLAY = (0, 255, 0, 128)
# Create game
pygame.init()
size = width, height = 1280, 720
screen = pygame.display.set_mode(size)
layout_style = "Classic"
# Fonts
OPEN_SANS = os.path.join(BASE_DIR, "assets", "fonts", "OpenSans-Regular.ttf")
smallFont = pygame.font.Font(OPEN_SANS, 20)
mediumFont = pygame.font.Font(OPEN_SANS, 28)
largeFont = pygame.font.Font(OPEN_SANS, 40)

# Compute board size
BOARD_PADDING = 20
board_width = ((2 / 3) * width) - (BOARD_PADDING * 2)
board_height = height - (BOARD_PADDING * 2)
cell_size = int(min(board_width / WIDTH, board_height / HEIGHT))
board_origin = (BOARD_PADDING, BOARD_PADDING)

# Add images
flag = pygame.image.load(os.path.join(BASE_DIR, "assets", "images", "flag.png"))
flag = pygame.transform.scale(flag, (cell_size, cell_size))

mine = pygame.image.load(os.path.join(BASE_DIR, "assets", "images", "mine.png"))
mine = pygame.transform.scale(mine, (cell_size, cell_size))

mine_red = pygame.image.load(os.path.join(BASE_DIR, "assets", "images", "mine-red.png"))
mine_red = pygame.transform.scale(mine_red, (cell_size, cell_size))

unrevealed = pygame.image.load(os.path.join(BASE_DIR, "assets", "images", "unrevealed.png"))
unrevealed = pygame.transform.scale(unrevealed, (cell_size, cell_size))
# Load number assets
numbers = []
for i in range(9):
    num_path = os.path.join(BASE_DIR, "assets", "images", f"{i}.png")
    num_img = pygame.image.load(num_path)
    num_img = pygame.transform.scale(num_img, (cell_size, cell_size))
    numbers.append(num_img)

# Detonated mine
mine_detonated = None

# Create game and AI agent
game = Minesweeper(height=HEIGHT, width=WIDTH, mines=MINES)
ai = MinesweeperAI(height=HEIGHT, width=WIDTH)

# Keep track of revealed cells, flagged cells, and if a mine was hit
revealed = set()
flags = set()
lost = False

# Show instructions initially
instructions = True

# Autoplay game
autoplay = False
autoplaySpeed = 0.3
makeAiMove = False

# Show Safe and Mine Cells
showInference = False

def flood_fill_reveal(cell):
    """
    Recursively reveals blank tiles (with 0 adjacent mines) and their neighbors.
    """
    queue = [cell]
    visited = set()

    while queue:
        current = queue.pop()
        if current in visited or current in revealed:
            continue
        visited.add(current)
        revealed.add(current)

        # Cập nhật AI với thông tin đầy đủ (nearby_mines)
        nearby = game.nearby_mines(current)
        ai.add_knowledge(current, nearby)

        if nearby == 0:
            i, j = current
            for ni in range(i - 1, i + 2):
                for nj in range(j - 1, j + 2):
                    if (
                        0 <= ni < HEIGHT and
                        0 <= nj < WIDTH and
                        (ni, nj) not in revealed and
                        (ni, nj) not in flags
                    ):
                        queue.append((ni, nj))

while True:

    # Check if game quit
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            sys.exit()

    screen.fill(BLACK)

    # Show game instructions
    if instructions:

        # Title
        title = largeFont.render("Play Minesweeper", True, WHITE)
        titleRect = title.get_rect()
        titleRect.center = ((width / 2), 50)
        screen.blit(title, titleRect)

        # Rules
        rules = [
            "Click a cell to reveal it.",
            "Right-click a cell to mark it as a mine.",
            "Mark all mines successfully to win!"
        ]
        for i, rule in enumerate(rules):
            line = smallFont.render(rule, True, WHITE)
            lineRect = line.get_rect()
            lineRect.center = ((width / 2), 150 + 30 * i)
            screen.blit(line, lineRect)

        # Play game button
        buttonRect = pygame.Rect((width / 4), (3 / 4) * height, width / 2, 50)
        buttonText = mediumFont.render("Play Game", True, BLACK)
        buttonTextRect = buttonText.get_rect()
        buttonTextRect.center = buttonRect.center
        pygame.draw.rect(screen, WHITE, buttonRect)
        screen.blit(buttonText, buttonTextRect)

        # Check if play button clicked
        click, _, _ = pygame.mouse.get_pressed()
        if click == 1:
            mouse = pygame.mouse.get_pos()
            if buttonRect.collidepoint(mouse):
                instructions = False
                time.sleep(0.3)

        pygame.display.flip()
        continue

    # Draw board
    cells = []
    for i in range(HEIGHT):
        row = []
        for j in range(WIDTH):

            # Draw rectangle for cell
            rect = pygame.Rect(
                board_origin[0] + j * cell_size,
                board_origin[1] + i * cell_size,
                cell_size, cell_size
            )
            if (i, j) not in revealed and (i, j) not in flags:
                screen.blit(unrevealed, rect)
                # Show inference overlay if enabled
                if showInference:
                    overlay = pygame.Surface((cell_size, cell_size), pygame.SRCALPHA)
                    if (i, j) in ai.safes:
                        overlay.fill(GREEN_OVERLAY)
                        screen.blit(overlay, rect)
                    elif (i, j) in ai.mines:
                        overlay.fill(RED_OVERLAY)
                        screen.blit(overlay, rect)
            else:
                pygame.draw.rect(screen, GRAY, rect)
                pygame.draw.rect(screen, BLACK, rect, 1)

            # Add a mine, flag, or number if needed
            if game.is_mine((i, j)) and lost:
                if (i,j) == mine_detonated:
                    screen.blit(mine_red, rect)
                else:
                    screen.blit(mine, rect)
            elif (i, j) in flags:
                screen.blit(flag, rect)
            elif (i, j) in revealed:
                mine_count = game.nearby_mines((i, j))
                screen.blit(numbers[mine_count], rect)
            row.append(rect)
        cells.append(row)

    # Autoplay Button
    autoplayBtn = pygame.Rect(
        (2 / 3) * width + BOARD_PADDING, BOARD_PADDING,
        (width / 3) - BOARD_PADDING * 2, 50
    )
    bText = "Autoplay" if not autoplay else "Stop"
    buttonText = mediumFont.render(bText, True, BLACK)
    buttonRect = buttonText.get_rect()
    buttonRect.center = autoplayBtn.center
    pygame.draw.rect(screen, WHITE, autoplayBtn)
    screen.blit(buttonText, buttonRect)

    # AI Move button
    aiButton = pygame.Rect(
        (2 / 3) * width + BOARD_PADDING, BOARD_PADDING + 70,
        (width / 3) - BOARD_PADDING * 2, 50
    )
    buttonText = mediumFont.render("AI Move", True, BLACK)
    buttonRect = buttonText.get_rect()
    buttonRect.center = aiButton.center
    if not autoplay:
        pygame.draw.rect(screen, WHITE, aiButton)
        screen.blit(buttonText, buttonRect)

    # Reset button
    resetButton = pygame.Rect(
        (2 / 3) * width + BOARD_PADDING, BOARD_PADDING + 140,
        (width / 3) - BOARD_PADDING * 2, 50
    )
    buttonText = mediumFont.render("Reset", True, BLACK)
    buttonRect = buttonText.get_rect()
    buttonRect.center = resetButton.center
    if not autoplay:
        pygame.draw.rect(screen, WHITE, resetButton)
        screen.blit(buttonText, buttonRect)

    # Display text
    text = ""
    if lost:
        text = "You Lose :("
    elif game.mines_initialized and len(revealed) == (HEIGHT * WIDTH - MINES):
        text = "You Win :D"
    text = mediumFont.render(text, True, WHITE)
    textRect = text.get_rect()
    textRect.center = ((5 / 6) * width, BOARD_PADDING + 232)
    screen.blit(text, textRect)

    # Show Safes and Mines button
    safesMinesButton = pygame.Rect(
        (2 / 3) * width + BOARD_PADDING, BOARD_PADDING + 280,
        (width / 3) - BOARD_PADDING * 2, 50
    )
    bText = "Show Inference" if not showInference else "Hide Inference"
    buttonText = smallFont.render(bText, True, BLACK)
    buttonRect = buttonText.get_rect()
    buttonRect.center = safesMinesButton.center
    if not autoplay:
        pygame.draw.rect(screen, WHITE, safesMinesButton)
        screen.blit(buttonText, buttonRect)

    move = None

    left, _, right = pygame.mouse.get_pressed()

    # Check for a right-click to toggle flagging
    if right == 1 and not lost and not autoplay:
        mouse = pygame.mouse.get_pos()
        for i in range(HEIGHT):
            for j in range(WIDTH):
                if cells[i][j].collidepoint(mouse) and (i, j) not in revealed:
                    if (i, j) in flags:
                        flags.remove((i, j))
                    else:
                        flags.add((i, j))
                    time.sleep(0.2)

    elif left == 1:
        mouse = pygame.mouse.get_pos()

        # If Autoplay button clicked, toggle autoplay
        if autoplayBtn.collidepoint(mouse):
            if not lost:
                autoplay = not autoplay
            else:
                autoplay = False
            time.sleep(0.2)
            continue

        # If AI button clicked, make an AI move
        elif aiButton.collidepoint(mouse) and not lost:
            makeAiMove = True
            time.sleep(0.2)

        # Reset game state
        elif resetButton.collidepoint(mouse):
            game = Minesweeper(height=HEIGHT, width=WIDTH, mines=MINES)
            ai = MinesweeperAI(height=HEIGHT, width=WIDTH)
            revealed = set()
            flags = set()
            lost = False
            mine_detonated = None
            continue

        # If Inference button clicked, toggle showInference
        elif safesMinesButton.collidepoint(mouse):
            showInference = not showInference
            time.sleep(0.2)

        # User-made move
        elif not lost:
            for i in range(HEIGHT):
                for j in range(WIDTH):
                    if (cells[i][j].collidepoint(mouse)
                            and (i, j) not in flags
                            and (i, j) not in revealed):
                        move = (i, j)

    # If autoplay, make move with AI
    if autoplay or makeAiMove:
        if makeAiMove:
            makeAiMove = False
        move = ai.make_safe_move()
        if move is None:
            move = ai.make_random_move()
            if move is None:
                flags = ai.mines.copy()
                print("No moves left to make.")
                autoplay = False
            else:
                print("No known safe moves, AI making random move.")
        else:
            print("AI making safe move.")

        # Add delay for autoplay
        if autoplay:
            time.sleep(autoplaySpeed)

    if move:
        if not game.mines_initialized:
            game.place_mines(move)
            game.mines_initialized = True

        if game.is_mine(move):
            lost = True
            mine_detonated = move
            autoplay = False
        else:
            nearby = game.nearby_mines(move)
            if nearby == 0:
                flood_fill_reveal(move)
            else:
                revealed.add(move)
            ai.add_knowledge(move, nearby)
            
    pygame.display.flip()
