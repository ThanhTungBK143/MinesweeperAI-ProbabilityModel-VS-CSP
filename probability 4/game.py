import random

class Minesweeper():
    """
    Minesweeper game representation
    """

    def __init__(self, height=8, width=8, mines=8):

        # Set initial width, height, and number of mines
        self.height = height
        self.width = width
        self.mines = set() #lưu tọa độ boom

        # Initialize an empty field with no mines
        self.board = []# tạo  dạng lưới 2d 
        for i in range(self.height):
            row = []
            for j in range(self.width):
                row.append(False)
            self.board.append(row)

        # Add mines randomly
        self.total_mines = mines
        self.first_move_made = False
        self.mines_initialized = False

        # At first, player has found no mines
        self.mines_found = set()

        self.total_mines = mines
        self.first_move_made = False # theo dõi các ô người chơi đánh dấu và ai đánh dấu 

    def print(self):
        # Prints a text-based representation of where mines are located.
        for i in range(self.height):
            print("--" * self.width + "-")
            for j in range(self.width):
                if self.board[i][j]:
                    print("|X", end="")
                else:
                    print("| ", end="")
            print("|")
        print("--" * self.width + "-")

    def is_mine(self, cell): # kiểm tra xem ô có phải là bom không
        i, j = cell
        return self.board[i][j]

    def nearby_mines(self, cell): # đếm mìn trong ô lân cận 
        """
        Returns the number of mines that are
        within one row and column of a given cell,
        not including the cell itself.
        """

        # Keep count of nearby mines
        count = 0

        # Loop over all cells within one row and column
        for i in range(cell[0] - 1, cell[0] + 2):
            for j in range(cell[1] - 1, cell[1] + 2):

                # Ignore the cell itself
                if (i, j) == cell:
                    continue

                # Update count if cell in bounds and is mine
                if 0 <= i < self.height and 0 <= j < self.width:
                    if self.board[i][j]:
                        count += 1

        return count

    def won(self):
        # Checks if all mines have been flagged.
        return self.mines_found == self.mines

    def place_mines(self, start_cell):
        # Đặt mìn, tránh ô đầu tiên và lân cận.
        i0, j0 = start_cell
        protected = set()
        for i in range(i0 - 1, i0 + 2):
            for j in range(j0 - 1, j0 + 2):
                if 0 <= i < self.height and 0 <= j < self.width:
                    protected.add((i, j))

        while len(self.mines) < self.total_mines:
            i = random.randrange(self.height)
            j = random.randrange(self.width)
            if (i, j) not in protected and (i, j) not in self.mines:
                self.mines.add((i, j))
                self.board[i][j] = True
    def flood_fill_reveal(self, cell, ai, revealed, flags):
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
            nearby = self.nearby_mines(current)
            ai.add_knowledge(current, nearby)
            if nearby == 0:
                i, j = current
                for ni in range(i - 1, i + 2):
                    for nj in range(j - 1, j + 2):
                        if (
                            0 <= ni < self.height and
                            0 <= nj < self.width and
                            (ni, nj) not in revealed and
                            (ni, nj) not in flags
                        ):
                            queue.append((ni, nj))

    def handle_move(self, move, ai, revealed, flags):
        """
        Handles a move made by the player or AI.
        Returns a tuple (lost, mine_detonated) to indicate game over state.
        """
        lost = False
        mine_detonated = None
        if not self.mines_initialized:
            self.place_mines(move)
            self.mines_initialized = True

        if self.is_mine(move):
            lost = True
            mine_detonated = move
        else:
            nearby = self.nearby_mines(move)
            if nearby == 0:
                self.flood_fill_reveal(move, ai, revealed, flags)
            else:
                revealed.add(move)
            ai.add_knowledge(move, nearby)

        return lost, mine_detonated

    def reset_game(self, height=None, width=None, mines=None):
        """
        Resets the game state.
        """
        if height: self.height = height
        if width: self.width = width
        if mines: self.total_mines = mines
        self.__init__(self.height, self.width, self.total_mines)
