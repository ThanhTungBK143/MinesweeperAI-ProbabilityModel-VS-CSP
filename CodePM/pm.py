import random

class MinesweeperAI:
    def __init__(self, height=9, width=9):
        self.height = height
        self.width = width
        self.moves_made = set()
        self.mines = set()
        self.safes = set()
        self.probabilities = {}

    def mark_mine(self, cell):
        self.mines.add(cell)
        self.probabilities[cell] = 1.0

    def mark_safe(self, cell):
        self.safes.add(cell)
        self.probabilities[cell] = 0.0

    def add_knowledge(self, cell, count):
        """
        Cập nhật xác suất mìn xung quanh cell dựa vào số mìn đếm được.
        """
        self.moves_made.add(cell)
        self.mark_safe(cell)

        neighbors = []
        known_mines = 0
        for i in range(cell[0]-1, cell[0]+2):
            for j in range(cell[1]-1, cell[1]+2):
                if 0 <= i < self.height and 0 <= j < self.width and (i,j) != cell:
                    if (i,j) in self.mines:
                        known_mines += 1
                    elif (i,j) not in self.safes and (i,j) not in self.moves_made:
                        neighbors.append((i,j))

        # Số mìn thực sự còn lại xung quanh ô này
        remaining = count - known_mines
        if remaining < 0: remaining = 0

        # Nếu tất cả neighbors là mìn
        if remaining == len(neighbors) and remaining > 0:
            for n in neighbors:
                self.mark_mine(n)
        # Nếu remaining = 0 -> tất cả neighbors an toàn
        elif remaining == 0:
            for n in neighbors:
                self.mark_safe(n)
        else:
            # Gán xác suất đều nhau
            prob = remaining / len(neighbors) if neighbors else 0
            for n in neighbors:
                # Nếu ô chưa có xác suất, gán trực tiếp; nếu có thì cập nhật bằng trung bình
                if n not in self.probabilities:
                    self.probabilities[n] = prob
                else:
                    # kết hợp bằng cách lấy max hoặc trung bình
                    self.probabilities[n] = max(self.probabilities[n], prob)

    def make_safe_move(self):
        candidates = [c for c in self.safes if c not in self.moves_made]
        return random.choice(candidates) if candidates else None

    def make_probabilistic_move(self):
        # chọn ô chưa mở có xác suất thấp nhất
        unknowns = [(c, self.probabilities.get(c, 0.5))
                    for i in range(self.height) for c in [(i,j) for j in range(self.width)]
                    if c not in self.moves_made and c not in self.mines]
        if not unknowns:
            return None
        # sắp xếp theo xác suất tăng dần
        unknowns.sort(key=lambda x: x[1])
        return unknowns[0][0]
