import pygame
import sys
import time
from game import Minesweeper
from csp import MinesweeperAI
import os

BASE_DIR = os.path.dirname(__file__)
# Default difficulty
HEIGHT = 9
WIDTH = 9
MINES = 10

# Colors
BLACK = (31, 31, 31)
GRAY = (192, 192, 192)
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
autoplay_start_time = None
autoplay_total_time = 0
autoplay_games = 0
autoplay_wins = 0
# Fonts
OPEN_SANS = os.path.join(BASE_DIR, "assets", "fonts", "mine-sweeper.ttf")
tinyFont = pygame.font.Font(OPEN_SANS, 16)
smallFont = pygame.font.Font(OPEN_SANS, 20)
mediumFont = pygame.font.Font(OPEN_SANS, 28)
largeFont = pygame.font.Font(OPEN_SANS, 40)

# Compute board size
BOARD_PADDING = 20
board_width = ((2 / 3) * width) - (BOARD_PADDING * 2)
board_height = height - (BOARD_PADDING * 2)
cell_size = int(min(board_width / WIDTH, board_height / HEIGHT))
board_origin = (BOARD_PADDING, BOARD_PADDING)
# Load the image once (outside your game loop)
icon_image = pygame.image.load(os.path.join(BASE_DIR, "assets", "images","flag.png")).convert_alpha()
icon_image = pygame.transform.scale(icon_image, (50, 50)) 
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
loop_autoplay = False

# Show Safe and Mine Cells
showInference = False

while True:

    # Check if game quit
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            sys.exit()

    screen.fill(BLACK)

    # Show game instructions
    if instructions:
        # Title
        title = largeFont.render("Minesweeper", True, WHITE)
        titleRect = title.get_rect()
        titleRect.center = ((width / 2), 50)
        screen.blit(title, titleRect)
        # Icon
        icon_rect_right = icon_image.get_rect()
        icon_rect_right.midleft = (titleRect.right + 20, titleRect.centery)  # 10px gap right side
        screen.blit(icon_image, icon_rect_right)
        icon_rect_left = icon_image.get_rect()
        icon_rect_left.midright = (titleRect.left - 20, titleRect.centery)   # 10px gap left side
        screen.blit(icon_image, icon_rect_left)

        # Rules
        rules = [
            "Left-click to reveal a tile",
            "The numbers show the nearby mines",  
            "Right-click to flag a mine",
            "Reveal all safe tiles to win!"  
        ]
        for i, rule in enumerate(rules):
            line = mediumFont.render(rule, True, WHITE)
            lineRect = line.get_rect()
            lineRect.center = ((width / 2), 150 + 50 * i)
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
    textRect.center = ((5 / 6) * width, BOARD_PADDING + 235)
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
        
    # Loop Autoplay Button
    loopAutoplayBtn = pygame.Rect(
        (2 / 3) * width + BOARD_PADDING, BOARD_PADDING + 350,
        (width / 3) - BOARD_PADDING * 2, 50
    )
    buttonText = smallFont.render("Loop Autoplay", True, BLACK)
    buttonRect = buttonText.get_rect()
    buttonRect.center = loopAutoplayBtn.center
    if not autoplay:
        pygame.draw.rect(screen, WHITE, loopAutoplayBtn)
        screen.blit(buttonText, buttonRect)

    # Display autoplay statistics
    if autoplay_games > 0:
        avg_speed = autoplay_total_time / autoplay_games
        win_rate = (autoplay_wins / autoplay_games) * 100
        games_text = tinyFont.render(
        f"Games Played: {autoplay_games}", True, WHITE
        )
        avg_speed_text = tinyFont.render(
            f"Avg Speed: {avg_speed:.2f} sec", True, WHITE
        )
        win_rate_text = tinyFont.render(
            f"Win Rate: {win_rate:.1f}%", True, WHITE
        )
        screen.blit(games_text, ((2 / 3) * width + BOARD_PADDING, BOARD_PADDING + 590))
        screen.blit(avg_speed_text, ((2 / 3) * width + BOARD_PADDING, BOARD_PADDING + 620))
        screen.blit(win_rate_text, ((2 / 3) * width + BOARD_PADDING, BOARD_PADDING + 650))

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
                if not autoplay:  # Starting autoplay
                    autoplay_start_time = time.time()
                else:  # Stopping autoplay manually
                    autoplay_total_time += time.time() - autoplay_start_time
                    autoplay_start_time = None
                    loop_autoplay = False  # Also stop loop mode
                autoplay = not autoplay
            else:
                autoplay = False
                loop_autoplay = False
            time.sleep(0.2)
            continue
        
        # Loop Autoplay button click
        if loopAutoplayBtn.collidepoint(mouse):
            if not lost:
                loop_autoplay = not loop_autoplay
                autoplay = loop_autoplay  # if loop starts, autoplay starts
                if loop_autoplay:
                    autoplay_start_time = time.time()
            else:
                loop_autoplay = False
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
            autoplay_games = 0
            autoplay_wins = 0
            autoplay_total_time = 0
            autoplay_start_time = None
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
        lost, mine_detonated_move = game.handle_move(move, ai, revealed, flags)
        if lost or (game.mines_initialized and len(revealed) == (HEIGHT * WIDTH - MINES)):
            if autoplay or loop_autoplay:
                autoplay_games += 1
                if not lost:
                    autoplay_wins += 1
                if autoplay_start_time:
                    autoplay_total_time += time.time() - autoplay_start_time
                    autoplay_start_time = None

            if lost:
                lost = True
                mine_detonated = mine_detonated_move

            if loop_autoplay:
                # Reset for next looped game WITHOUT counting again
                game = Minesweeper(height=HEIGHT, width=WIDTH, mines=MINES)
                ai = MinesweeperAI(height=HEIGHT, width=WIDTH)
                revealed.clear()
                flags.clear()
                lost = False
                mine_detonated = None
                autoplay_start_time = time.time()
                autoplay = True
            else:
                autoplay = False
            
    pygame.display.flip()
