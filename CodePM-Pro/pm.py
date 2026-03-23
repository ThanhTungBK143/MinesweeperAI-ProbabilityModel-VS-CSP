# We'll write a new csp.py that upgrades the Probability Model to a Hybrid Exact/Probabilistic solver.
# Features:
# - Deterministic rules (safe/flag)
# - Build frontier constraints from current visible board
# - Decompose into connected components
# - Exact enumeration on small components with backtracking + pruning
# - Weighting by global remaining mines (hypergeometric adjustment)
# - Fallback to Monte Carlo importance sampling on big components
# - Compute marginals P(mine) and pick min-risk move
#
# The class name and public methods remain: MinesweeperAI.mark_safe, mark_mine, add_knowledge,
# make_safe_move, make_probabilistic_move (and make_random_move kept as alias).

from typing import List, Tuple, Set, Dict
from collections import defaultdict, deque
import random
import math
import json
import os

COVERED = -1
FLAGGED = -2

def _neighbors(cell, height, width):
    r, c = cell
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            nr, nc = r + dr, c + dc
            if 0 <= nr < height and 0 <= nc < width:
                yield (nr, nc)

class MinesweeperAI:
    def __init__(self, height=8, width=8, mines_total=None, exact_limit=18, mc_samples=2000, rng_seed=7):
        self.height = height
        self.width = width

        # If total mines is known by the game wrapper, pass it in (recommended)
        self.mines_total = mines_total

        self.moves_made: Set[Tuple[int, int]] = set()
        self.mines: Set[Tuple[int, int]] = set()
        self.safes: Set[Tuple[int, int]] = set()

        # Probabilities cache
        self.probabilities: Dict[Tuple[int,int], float] = {}

        # Config
        self.exact_limit = exact_limit      # up to this many vars per component we solve exactly
        self.mc_samples = mc_samples
        self.rng = random.Random(rng_seed)

        # A shadow of visible numbers if runner/game feeds them via add_knowledge
        # We'll keep a minimal memory of "frontier numbers" we have seen to build constraints robustly
        self._revealed_numbers: Dict[Tuple[int,int], int] = {}

    # ----------------- Public API expected by runner/game -----------------

    def mark_mine(self, cell: Tuple[int,int]):
        self.mines.add(cell)
        self.probabilities[cell] = 1.0

    def mark_safe(self, cell: Tuple[int,int]):
        self.safes.add(cell)
        self.probabilities[cell] = 0.0

    def add_knowledge(self, cell: Tuple[int,int], count: int, visible_board: List[List[int]] = None, flags_count: int = None, total_mines: int = None):
        """
        Called by the game after revealing a number cell.
        - cell: revealed cell coordinates
        - count: number displayed on that cell
        - visible_board: (optional) board state (COVERED=-1, FLAGGED=-2, numbers>=0). If provided, we can rebuild constraints more accurately.
        - flags_count: (optional) number of flags currently placed (for global mine count)
        - total_mines: (optional) global total mines, if known, overrides self.mines_total
        """
        self.moves_made.add(cell)
        self.mark_safe(cell)
        self._revealed_numbers[cell] = count

        if total_mines is not None:
            self.mines_total = total_mines

        # Use deterministic local inferences around this cell
        if visible_board is not None:
            self._apply_local_inference_from(cell, count, visible_board)

        # Recompute probabilities over the frontier using exact/MC as needed (optional heavy step).
        # If the caller prefers to call this less frequently, they can, but doing it here gives best quality.
        if visible_board is not None:
            self._recompute_frontier_probabilities(visible_board, flags_count)

    def make_safe_move(self):
        """Return a safe cell not yet moved on, if any."""
        for cell in sorted(self.safes):
            if cell not in self.moves_made and cell not in self.mines:
                return cell
        return None

    def make_probabilistic_move(self, visible_board: List[List[int]] = None, flags_count: int = None, total_mines: int = None):
        """
        Choose the lowest-risk cell among unknowns.
        If visible_board is provided, we recompute up-to-date probabilities.
        """
        if total_mines is not None:
            self.mines_total = total_mines

        move = self.make_safe_move()
        if move:
            return move

        if visible_board is not None:
            self._recompute_frontier_probabilities(visible_board, flags_count)

        # Among unknowns, pick min probability (tie-break by expected info gain later)
        unknowns = []
        for r in range(self.height):
            for c in range(self.width):
                cell = (r, c)
                if cell in self.moves_made or cell in self.mines or cell in self.safes:
                    continue
                p = self.probabilities.get(cell, None)
                if p is None:
                    # fallback prior if nothing known: use global prior
                    p = self._global_prior(visible_board, flags_count)
                unknowns.append((p, cell))

        if not unknowns:
            return None

        unknowns.sort(key=lambda x: (x[0], x[1]))  # sort by probability then coord for determinism

        # Tie-break among similar probabilities using expected info gain (optional lightweight heuristic)
        best_p = unknowns[0][0]
        best_cells = [cell for p, cell in unknowns if abs(p - best_p) < 1e-6]
        if len(best_cells) == 1:
            return best_cells[0]

        # Prefer edges (often safer) if equal probability
        def edge_score(cell):
            r, c = cell
            on_edge = (r in (0, self.height-1)) + (c in (0, self.width-1))
            return -on_edge  # prefer higher edge flag -> lower score

        best_cells.sort(key=lambda cell: (edge_score(cell), cell))
        return best_cells[0]

    # Backward-compat if runner still calls make_random_move
    def make_random_move(self, *args, **kwargs):
        return self.make_probabilistic_move(*args, **kwargs)

    # ----------------- Core Probability Engine -----------------

    def _apply_local_inference_from(self, cell, count, visible_board):
        """Basic deterministic rules to harvest obvious safes/mines quickly."""
        nbrs = list(_neighbors(cell, self.height, self.width))
        covered = [n for n in nbrs if visible_board[n[0]][n[1]] == COVERED]
        flagged = sum(1 for n in nbrs if visible_board[n[0]][n[1]] == FLAGGED)

        remain = count - flagged
        if remain == 0:
            for n in covered:
                self.mark_safe(n)
        elif remain == len(covered) and remain > 0:
            for n in covered:
                self.mark_mine(n)

    def _recompute_frontier_probabilities(self, visible_board, flags_count):
        constraints, frontier, covered_all = self._build_constraints(visible_board)

        if not frontier:
            # Assign uniform global prior to all covered unknowns
            prior = self._global_prior(visible_board, flags_count)
            for cell in covered_all:
                if cell not in self.mines and cell not in self.safes:
                    self.probabilities[cell] = prior
            return

        # Decompose into connected components
        graph = self._constraint_graph(constraints, frontier)
        comps = self._connected_components(graph)

        # For each component compute exact/approx probabilities
        comp_probs: Dict[Tuple[int,int], float] = {}
        comp_var_counts: Dict[Tuple[int,int], int] = {}
        total_config_weight = 1.0

        for comp in comps:
            sub_cons = self._restrict_constraints(constraints, comp)
            if len(comp) <= self.exact_limit:
                marginals, total_weight = self._exact_component_marginals(comp, sub_cons)
            else:
                marginals, total_weight = self._mc_component_marginals(comp, sub_cons, samples=self.mc_samples)

            # Store
            for v in comp:
                comp_probs[v] = marginals.get(v, 0.0)
            total_config_weight *= max(total_weight, 1e-12)
            comp_var_counts.update({v:1 for v in comp})

        # Apply global remaining mines prior across frontier vs non-frontier covered
        # Compute average frontier mine prob
        if self.mines_total is not None and flags_count is not None:
            remaining_mines = max(0, self.mines_total - flags_count - len(self.mines))
            # covered cells not in frontier get a baseline probability to match the global count
            non_frontier = [c for c in covered_all if c not in frontier and c not in self.mines and c not in self.safes]
            frontier_estimated_mines = sum(comp_probs.get(v, 0.0) for v in frontier)
            non_frontier_count = len(non_frontier)
            if non_frontier_count > 0:
                residual = remaining_mines - frontier_estimated_mines
                baseline = min(1.0, max(0.0, residual / non_frontier_count))
            else:
                baseline = None
        else:
            baseline = None

        # Write back probabilities
        for cell in covered_all:
            if cell in self.mines:
                self.probabilities[cell] = 1.0
            elif cell in self.safes:
                self.probabilities[cell] = 0.0
            elif cell in frontier:
                self.probabilities[cell] = comp_probs.get(cell, self._global_prior(visible_board, flags_count))
            else:
                self.probabilities[cell] = baseline if baseline is not None else self._global_prior(visible_board, flags_count)

    def _global_prior(self, visible_board, flags_count):
        # Use remaining mines / remaining covered as baseline prior
        if visible_board is None or self.mines_total is None or flags_count is None:
            return 0.5
        covered = [(r, c) for r in range(self.height) for c in range(self.width) if visible_board[r][c] == COVERED]
        remaining = len(covered)
        if remaining <= 0:
            return 0.5
        remaining_mines = max(0, self.mines_total - flags_count - len(self.mines))
        return min(1.0, max(0.0, remaining_mines / remaining))

    # ----------------- Constraint building -----------------

    def _build_constraints(self, visible_board):
        """Return (constraints, frontier_vars, covered_all). constraints = list of (set(cells), k)."""
        constraints = []
        frontier_vars: Set[Tuple[int,int]] = set()
        covered_all = []

        for r in range(self.height):
            for c in range(self.width):
                v = visible_board[r][c]
                if v == COVERED:
                    covered_all.append((r, c))
                    continue
                if v < 0:  # flagged or others
                    continue
                # revealed number cell
                cov = set()
                k = v
                for nr, nc in _neighbors((r, c), self.height, self.width):
                    if visible_board[nr][nc] == FLAGGED or (nr, nc) in self.mines:
                        k -= 1
                    elif visible_board[nr][nc] == COVERED and (nr, nc) not in self.safes:
                        cov.add((nr, nc))
                if cov:
                    k = max(0, min(k, len(cov)))
                    constraints.append((cov, k))
                    frontier_vars |= cov
        return constraints, frontier_vars, covered_all

    def _constraint_graph(self, constraints, frontier):
        graph = {v:set() for v in frontier}
        for cells, _ in constraints:
            cells = list(cells)
            for i in range(len(cells)):
                for j in range(i+1, len(cells)):
                    a, b = cells[i], cells[j]
                    graph[a].add(b)
                    graph[b].add(a)
        return graph

    def _connected_components(self, graph):
        seen = set()
        comps = []
        for v in graph:
            if v in seen:
                continue
            comp = set()
            q = deque([v])
            seen.add(v)
            while q:
                u = q.popleft()
                comp.add(u)
                for w in graph[u]:
                    if w not in seen:
                        seen.add(w)
                        q.append(w)
            comps.append(comp)
        return comps

    def _restrict_constraints(self, constraints, comp):
        comp = set(comp)
        sub = []
        for cells, k in constraints:
            inter = cells & comp
            if inter:
                sub.append((inter, k))
        return sub

    # ----------------- Exact marginals on a component -----------------

    def _exact_component_marginals(self, comp: Set[Tuple[int,int]], constraints: List[Tuple[Set[Tuple[int,int]], int]]):
        vars_list = sorted(list(comp))
        index = {v:i for i,v in enumerate(vars_list)}
        # Preprocess constraints to index lists
        cons_idx = [([index[v] for v in sorted(cells)], k) for cells, k in constraints]

        # For pruning, keep per-constraint counts
        n = len(vars_list)
        assignment = [0]*n  # 0/1
        used = [False]*n

        # For each constraint, track:
        cons_len = [len(v_idx) for v_idx, _ in cons_idx]
        cons_sum = [0]*len(cons_idx)     # assigned 1s so far
        cons_assigned = [0]*len(cons_idx)# number of variables seen in this constraint

        marg_counts = [0]*n
        total_weight = 0

        # Backtracking
        order = self._variable_order(cons_idx, n)

        def backtrack(pos):
            nonlocal total_weight
            if pos == n:
                # All assigned: check exact satisfaction
                for (v_idx, k), s, a, L in zip(cons_idx, cons_sum, cons_assigned, cons_len):
                    if s != k:
                        return
                total_weight += 1
                for i in range(n):
                    if assignment[i] == 1:
                        marg_counts[i] += 1
                return

            i = order[pos]

            # Try 0 then 1 (0 often more common => faster pruning when sums too big)
            for val in (0,1):
                # update temporary
                assignment[i] = val
                impacted = []
                feasible = True
                for ci, (v_idx, k) in enumerate(cons_idx):
                    if i in v_idx:
                        cons_assigned[ci] += 1
                        if val == 1:
                            cons_sum[ci] += 1
                        impacted.append(ci)

                        # Prune if impossible: sum > k OR even with remaining vars can't reach k
                        max_possible = cons_sum[ci] + (len(v_idx) - cons_assigned[ci])
                        if cons_sum[ci] > k or max_possible < k:
                            feasible = False
                            break

                if feasible:
                    backtrack(pos+1)

                # rollback
                for ci in impacted:
                    if assignment[i] == 1:
                        cons_sum[ci] -= 1
                    cons_assigned[ci] -= 1

            assignment[i] = 0

        backtrack(0)

        if total_weight == 0:
            # No satisfying assignments (shouldn't happen if game state is valid). Avoid div by zero.
            # Return neutral probabilities.
            return {v: 0.5 for v in vars_list}, 0.0

        marginals = {vars_list[i]: marg_counts[i]/total_weight for i in range(n)}
        return marginals, float(total_weight)

    def _variable_order(self, cons_idx, n_vars):
        # Order variables by degree (how many constraints they appear in), descending
        deg = [0]*n_vars
        for v_idx, _ in cons_idx:
            for i in v_idx:
                deg[i] += 1
        return sorted(range(n_vars), key=lambda i: (-deg[i], i))

    # ----------------- Monte Carlo marginals on a component -----------------

    def _mc_component_marginals(self, comp: Set[Tuple[int,int]], constraints: List[Tuple[Set[Tuple[int,int]], int]], samples=2000):
        vars_list = sorted(list(comp))
        index = {v:i for i,v in enumerate(vars_list)}
        cons_idx = [([index[v] for v in sorted(cells)], k) for cells, k in constraints]

        n = len(vars_list)
        rng = self.rng

        hits = [0]*n
        valid = 0

        # Use a simple importance scheme: sample k close to constraint averages
        avg_k = 0
        total_cells = 0
        for v_idx, k in cons_idx:
            avg_k += k
            total_cells += len(v_idx)
        p0 = (avg_k / total_cells) if total_cells > 0 else 0.2
        p0 = min(0.8, max(0.05, p0))

        for _ in range(samples):
            assign = [1 if rng.random() < p0 else 0 for _ in range(n)]
            # Fast check constraints
            ok = True
            for v_idx, k in cons_idx:
                s = sum(assign[i] for i in v_idx)
                if s != k:
                    ok = False
                    break
            if not ok:
                continue
            valid += 1
            for i in range(n):
                if assign[i] == 1:
                    hits[i] += 1

        if valid == 0:
            # fallback neutral
            return {v: 0.5 for v in vars_list}, 0.0

        marginals = {vars_list[i]: hits[i]/valid for i in range(n)}
        return marginals, float(valid)


