
import random
from collections import Counter


def genetic_algorithm(
    subjects,
    timeslots,
    priorities,
    credits,
    invalid_slots=None,
    blocked_days=None,
    generations=50,
    population_size=20,
):
    """
    TRUE Genetic Algorithm for conflict-free academic timetable generation.

    Encoding: Indirect (ordering/permutation) encoding.
      - Chromosome = a permutation of the subject pool (subjects repeated by credit count)
      - Phenotype  = schedule decoded from chromosome via greedy slot assignment
      - Sunday is always blocked (not in days list).
      - Additional blocked_days (holidays) are also excluded.

    Components:
      - Population initialisation  : random shuffles of subject pool
      - Fitness function           : penalty/reward scoring of decoded schedule
      - Parent selection           : k=3 Tournament Selection
      - Crossover                  : Single-cut Order Crossover (OX) preserving multiset
      - Mutation                   : Swap Mutation at rate=0.10
      - Elitism                    : top elite_count chromosomes carried forward unchanged
      - Adaptive mutation          : rate increases by 15% every 25 generations

    Args:
        subjects      : list of subject name strings
        timeslots     : list of time strings e.g. ["08:00:00", "09:00:00", ...]
        priorities    : dict {subject_name: int priority 1-5}
        credits       : dict {subject_name: int credit_count}
        invalid_slots : dict {subject: set of (day, time_str) tuples teacher is busy}
        blocked_days  : list of day names to block e.g. ["Wednesday", "Saturday"]
        generations   : number of GA generations (default 50)
        population_size: size of population (default 20)

    Returns:
        list of {"subject": str, "day": str, "timeslot": str} dicts
    """

    # ── Defaults ──────────────────────────────────────────────────────────────
    if invalid_slots is None:
        invalid_slots = {}
    if blocked_days is None:
        blocked_days = []

    # ── Available days (Sunday always excluded; blocked_days also removed) ────
    ALL_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    available_days = [d for d in ALL_DAYS if d not in blocked_days]
    if not available_days:
        available_days = ALL_DAYS  # Safety fallback

    # ── All (day, timeslot) pairs ─────────────────────────────────────────────
    all_slots = [(day, slot) for day in available_days for slot in timeslots]

    # ── Subject pool: each subject repeated by its credit count ──────────────
    class_pool: list[str] = []
    for subject, count in credits.items():
        class_pool.extend([subject] * count)

    if not class_pool or not all_slots:
        return []

    pool_counts = Counter(class_pool)
    total_needed = len(class_pool)
    time_idx_map = {t: i for i, t in enumerate(timeslots)}

    # High-priority subjects: those at or near the maximum priority
    max_p = max(priorities.values()) if priorities else 0
    high_priority_subjects = {s for s, p in priorities.items() if p >= max(1, max_p - 1)}

    # ═══════════════════════════════════════════════════════════════════════════
    # DECODE  — chromosome (ordering) → concrete schedule
    # ═══════════════════════════════════════════════════════════════════════════
    def decode(ordering: list[str]):
        """
        Greedy decoder: assign each subject in chromosome order to the next
        available valid (day, timeslot) slot.

        Hard constraints enforced:
          - No two subjects share the same (day, timeslot)
          - No subject placed in a slot marked invalid for it (faculty busy / break)
          - Max 2 lectures per subject per day
          - No lectures on blocked days
        Returns list of entry dicts or None if infeasible.
        """
        schedule = []
        slots = all_slots[:]          # Work on a copy; ordering is fixed
        subject_day_counts: dict = {}

        for subj in ordering:
            assigned = False
            constraints = invalid_slots.get(subj, set())
            for i, (day, time) in enumerate(slots):
                if (
                    subject_day_counts.get((subj, day), 0) < 2
                    and (day, time) not in constraints
                ):
                    schedule.append({"subject": subj, "day": day, "timeslot": time})
                    slots.pop(i)
                    subject_day_counts[(subj, day)] = (
                        subject_day_counts.get((subj, day), 0) + 1
                    )
                    assigned = True
                    break
            if not assigned:
                return None   # Chromosome is infeasible for current constraints

        return schedule

    # ═══════════════════════════════════════════════════════════════════════════
    # FITNESS FUNCTION
    # ═══════════════════════════════════════════════════════════════════════════
    def calculate_fitness(ordering: list[str]) -> float:
        """
        Decode chromosome and score the resulting schedule.

        Rewards:
          +100  per unique subject on a day (variety)
          +30   per subject per day (spreading across days)
          +2×p  per lecture (general priority reward, p = priority value)
          +20×p for each consecutive pair of high-priority lectures on same day

        Penalties:
          -500×(k-2) if a subject appears >2 times on same day (k = excess count)
          -20        if a non-high-priority subject has 2 lectures on same day
          -100×count if multi-lectures on same day are NOT in consecutive time slots
        """
        schedule = decode(ordering)
        if schedule is None:
            return float("-inf")

        score = 0.0
        day_map: dict = {day: [] for day in available_days}
        for entry in schedule:
            day_map[entry["day"]].append(entry)

        for day, entries in day_map.items():
            entries.sort(key=lambda x: time_idx_map.get(x["timeslot"], 0))
            sub_slots: dict = {}

            for i, entry in enumerate(entries):
                subj = entry["subject"]
                idx = time_idx_map.get(entry["timeslot"], 0)
                sub_slots.setdefault(subj, []).append(idx)

                # Bonus: consecutive high-priority pair
                if i > 0:
                    prev = entries[i - 1]
                    prev_idx = time_idx_map.get(prev["timeslot"], 0)
                    if (
                        prev["subject"] == subj
                        and subj in high_priority_subjects
                        and idx == prev_idx + 1
                    ):
                        score += 20 * priorities.get(subj, 1)

                # General priority reward per lecture
                score += priorities.get(subj, 1) * 2

            # Variety reward: unique subjects on this day
            score += len(sub_slots) * 100

            for subj, idxs in sub_slots.items():
                count = len(idxs)
                if count > 2:
                    score -= (count - 2) * 500        # Heavy over-limit penalty
                elif count == 2 and subj not in high_priority_subjects:
                    score -= 20                        # Minor double-lecture penalty
                if count >= 2:
                    s_idxs = sorted(idxs)
                    if s_idxs[-1] - s_idxs[0] != count - 1:
                        score -= 100 * count           # Non-contiguous penalty
                score += 30                            # Spreading bonus

        return score

    # ═══════════════════════════════════════════════════════════════════════════
    # TOURNAMENT SELECTION  (k = 3)
    # ═══════════════════════════════════════════════════════════════════════════
    def tournament_selection(
        population: list, fitnesses: list, k: int = 3
    ) -> list:
        """
        Pick k random chromosomes and return a copy of the fittest one.
        Provides selection pressure while maintaining diversity.
        """
        k = min(k, len(population))
        contestants = random.sample(range(len(population)), k)
        winner = max(contestants, key=lambda i: fitnesses[i])
        return population[winner][:]

    # ═══════════════════════════════════════════════════════════════════════════
    # CROSSOVER  — Single-cut Order Crossover (OX) for multisets
    # ═══════════════════════════════════════════════════════════════════════════
    def crossover(parent1: list, parent2: list) -> list:
        """
        Produces one child from two parents.

        Method:
          1. Choose a random cut point.
          2. Child inherits parent1[0:cut] exactly.
          3. Remaining genes are filled from parent2 (in order) while
             respecting the required multiset counts from class_pool.

        This guarantees the child is always a valid permutation of class_pool.
        """
        n = len(parent1)
        if n < 2:
            return parent1[:]

        cut = random.randint(1, n - 1)
        child = parent1[:cut]

        # Track how many of each subject we still need to add
        placed = Counter(child)
        remaining_needed = {s: pool_counts[s] - placed.get(s, 0) for s in pool_counts}

        # Fill from parent2 in order
        for item in parent2:
            if remaining_needed.get(item, 0) > 0:
                child.append(item)
                remaining_needed[item] -= 1

        return child

    # ═══════════════════════════════════════════════════════════════════════════
    # MUTATION  — Swap Mutation
    # ═══════════════════════════════════════════════════════════════════════════
    def mutate(chromosome: list, rate: float = 0.10) -> list:
        """
        With probability `rate` for each gene, swap it with a random gene.
        Preserves the multiset (only reorders), so decoded schedule remains
        structurally valid.
        """
        ch = chromosome[:]
        for i in range(len(ch)):
            if random.random() < rate:
                j = random.randint(0, len(ch) - 1)
                ch[i], ch[j] = ch[j], ch[i]
        return ch

    # ═══════════════════════════════════════════════════════════════════════════
    # INITIALISE POPULATION
    # ═══════════════════════════════════════════════════════════════════════════
    population: list[list] = []
    for _ in range(population_size):
        chrom = class_pool[:]
        random.shuffle(chrom)
        population.append(chrom)

    elite_count = max(2, population_size // 10)   # Top 10% survive unchanged
    mutation_rate = 0.10
    best_chromosome = None
    best_fitness = float("-inf")

    # ═══════════════════════════════════════════════════════════════════════════
    # GENERATIONAL EVOLUTION LOOP
    # ═══════════════════════════════════════════════════════════════════════════
    for generation in range(generations):

        # 1. Evaluate all chromosomes
        fitnesses = [calculate_fitness(ch) for ch in population]

        # 2. Track global best (elitism across all generations)
        gen_best_idx = max(range(len(fitnesses)), key=lambda i: fitnesses[i])
        if fitnesses[gen_best_idx] > best_fitness:
            best_fitness = fitnesses[gen_best_idx]
            best_chromosome = population[gen_best_idx][:]

        # 3. Sort population by fitness descending
        pairs = sorted(zip(fitnesses, population), key=lambda x: x[0], reverse=True)
        sorted_fits = [f for f, _ in pairs]
        sorted_pop = [ch for _, ch in pairs]

        # 4. Elitism: carry top elite_count unchanged
        new_pop = [ch[:] for ch in sorted_pop[:elite_count]]

        # 5. Fill remainder via selection → crossover → mutation
        while len(new_pop) < population_size:
            p1 = tournament_selection(sorted_pop, sorted_fits, k=3)
            p2 = tournament_selection(sorted_pop, sorted_fits, k=3)
            child = crossover(p1, p2)
            child = mutate(child, mutation_rate)
            new_pop.append(child)

        population = new_pop

        # 6. Adaptive mutation: nudge rate up every 25 generations to escape local optima
        if generation > 0 and generation % 25 == 0:
            mutation_rate = min(0.30, mutation_rate * 1.15)

    # ═══════════════════════════════════════════════════════════════════════════
    # DECODE BEST CHROMOSOME
    # ═══════════════════════════════════════════════════════════════════════════
    if best_chromosome:
        result = decode(best_chromosome)
        if result:
            return result

    # Fallback: try each population member in case best chromosome decodes None
    for ch in population:
        result = decode(ch)
        if result:
            return result

    return []
