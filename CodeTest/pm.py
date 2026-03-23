import itertools
import random

class Sentence():
    """
    Logical statement about a Minesweeper game
    A sentence consists of a set of board cells,
    and a count of the number of those cells which are mines.
    """

    def __init__(self, cells, count):
        self.cells = set(cells)
        self.count = count

    def __eq__(self, other):
        return self.cells == other.cells and self.count == other.count

    def __str__(self):
        return f"{self.cells} = {self.count}"

    def known_mines(self):
        if len(self.cells) == self.count and self.count != 0:
            return self.cells
        return set()

    def known_safes(self):
        if self.count == 0:
            return self.cells
        return set()

    def mark_mine(self, cell):
        if cell in self.cells:
            self.cells.remove(cell)
            self.count -= 1

    def mark_safe(self, cell):
        if cell in self.cells:
            self.cells.remove(cell)

class MinesweeperAI():
    """
    Minesweeper game player using Probability Model
    """

    def __init__(self, height=8, width=8):
        self.height = height
        self.width = width
        self.moves_made = set()
        self.mines = set()
        self.safes = set()
        self.knowledge = []

    def mark_mine(self, cell):
        if cell not in self.mines:
            self.mines.add(cell)
            for sentence in self.knowledge:
                sentence.mark_mine(cell)

    def mark_safe(self, cell):
        if cell not in self.safes:
            self.safes.add(cell)
            for sentence in self.knowledge:
                sentence.mark_safe(cell)
    
    def add_knowledge(self, cell, count):
        self.mark_safe(cell)
        self.moves_made.add(cell)
        
        neighbors, count = self.get_cell_neighbors(cell, count)
        
        if len(neighbors) == 0:
            return

        new_sentence = Sentence(neighbors, count)
        
        if new_sentence not in self.knowledge:
            self.knowledge.append(new_sentence)

        self.infer_new_knowledge()
        
    def infer_new_knowledge(self):
        inferred_something = True
        while inferred_something:
            inferred_something = False

            self.knowledge = [s for s in self.knowledge if len(s.cells) > 0]

            new_mines = set()
            new_safes = set()
            for sentence in self.knowledge:
                new_mines.update(sentence.known_mines())
                new_safes.update(sentence.known_safes())
            
            if new_mines or new_safes:
                inferred_something = True
                for cell in new_safes:
                    self.mark_safe(cell)
                for cell in new_mines:
                    self.mark_mine(cell)

            new_inferences = []
            for s1 in self.knowledge:
                for s2 in self.knowledge:
                    if s1 is s2 or s1.cells == s2.cells:
                        continue
                    
                    if s1.cells.issubset(s2.cells):
                        inferred_something = True
                        new_cells = s2.cells - s1.cells
                        new_count = s2.count - s1.count
                        new_sentence = Sentence(new_cells, new_count)
                        if new_sentence not in self.knowledge and new_sentence not in new_inferences:
                            new_inferences.append(new_sentence)

            self.knowledge.extend(new_inferences)
            
    def make_safe_move(self):
        safe_moves = self.safes - self.moves_made
        if safe_moves:
            return safe_moves.pop()
        return None

    def make_probabilistic_move(self):
        probabilities = {}
        
        mine_possibilities = self.calculate_probabilities()
        
        for cell, prob in mine_possibilities.items():
            probabilities[cell] = prob
            
        if not probabilities:
            return self.make_random_move()
            
        min_prob = min(probabilities.values())
        best_moves = [cell for cell, prob in probabilities.items() if prob == min_prob]

        return random.choice(best_moves)

    def calculate_probabilities(self):
        mine_possibilities = {}
        
        for sentence in self.knowledge:
            cells_to_consider = list(sentence.cells)
            count = sentence.count
            
            for subset in itertools.combinations(cells_to_consider, count):
                is_valid = True
                for other_sentence in self.knowledge:
                    if other_sentence is sentence:
                        continue
                        
                    mine_count_in_other = sum(1 for cell in subset if cell in other_sentence.cells)
                    
                    if not (0 <= mine_count_in_other <= len(other_sentence.cells) and 
                            mine_count_in_other >= other_sentence.count - (len(other_sentence.cells) - len(subset))) :
                        is_valid = False
                        break

                if is_valid:
                    for cell in subset:
                        mine_possibilities[cell] = mine_possibilities.get(cell, 0) + 1
                    for cell in (sentence.cells - set(subset)):
                        mine_possibilities[cell] = mine_possibilities.get(cell, 0) + 0

        total_possibilities = sum(mine_possibilities.values())
        if total_possibilities > 0:
            for cell in mine_possibilities:
                mine_possibilities[cell] /= total_possibilities
        
        return mine_possibilities
               
    def get_cell_neighbors(self, cell, count):
        i, j = cell
        neighbors = set()
        mines_in_neighbors = 0
        
        for row in range(i - 1, i + 2):
            for col in range(j - 1, j + 2):
                if (row >= 0 and row < self.height and
                        col >= 0 and col < self.width and
                        (row, col) != cell):
                    
                    neighbor_cell = (row, col)
                    if neighbor_cell in self.mines:
                        mines_in_neighbors += 1
                    elif neighbor_cell not in self.safes:
                        neighbors.add(neighbor_cell)
        
        return neighbors, count - mines_in_neighbors
    
    def make_random_move(self):
        all_moves = set()
        for i in range(self.height):
            for j in range(self.width):
                cell = (i, j)
                if cell not in self.moves_made and cell not in self.mines:
                    all_moves.add(cell)
        
        if len(all_moves) == 0:
            return None
            
        return random.choice(list(all_moves))

    def next_move(self):
        move = self.make_safe_move()
        if move:
            return move
        move = self.make_probabilistic_move()
        if move:
            return move
        return self.make_random_move()
