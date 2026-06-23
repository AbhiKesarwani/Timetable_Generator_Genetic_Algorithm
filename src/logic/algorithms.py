
import random
from collections import Counter
from copy import deepcopy


def genetic_algorithm(
    subjects,
    timeslots,
    priorities,
    credits,
    invalid_slots=None,
    blocked_days=None,
    faculty_busy_slots=None,
    subject_faculty_map=None,
    generations=50,
    population_size=20,
):
    """
    Faculty-Aware Genetic Algorithm for conflict-free academic timetable generation.

    Encoding: Indirect (ordering/permutation) encoding.
      - Chromosome = a permutation of the subject pool (subjects repeated by credit count)
      - Phenotype  = schedule decoded from chromosome via greedy slot assignment
      - Sunday is always blocked (not in days list).
      - Additional blocked_days (holidays) are also excluded.

    Faculty Hard Constraint (NEW):
      - Each chromosome evaluation works on its OWN deepcopy of faculty_busy_slots.
      - Before assigning any (day, time) slot, the faculty member's busy set is checked.
      - If the faculty is already occupied, the slot is SKIPPED — never assigned.
      - As slots are assigned, they are added to the local copy immediately.
      - This makes faculty conflicts IMPOSSIBLE within a single schedule.

    Args:
        subjects          : list of subject name strings
        timeslots         : list of time strings e.g. ["08:00:00", "09:00:00", ...]
        priorities        : dict {subject_name: int priority 1-5}
        credits           : dict {subject_name: int credit_count}
        invalid_slots     : dict {subject: set of (day, time_str)} — break slots + legacy
        blocked_days      : list of day names to block e.g. ["Wednesday", "Saturday"]
        faculty_busy_slots: dict {teacher_id: set of (day, time_str)} — cross-class
                            occupancy loaded from DB BEFORE deleting current class rows.
                            This is the GLOBAL pre-existing occupancy.
        subject_faculty_map: dict {subject_name: teacher_id}
        generations       : number of GA generations (default 50)
        population_size   : size of population (default 20)

    Returns:
        (schedule, unscheduled_list) where:
          schedule         = list of {"subject": str, "day": str, "timeslot": str}
          unscheduled_list = list of {"subject": str, "reason": str}
    """

    # ── Defaults ──────────────────────────────────────────────────────────────
    if invalid_slots is None:
        invalid_slots = {}
    if blocked_days is None:
        blocked_days = []
    if faculty_busy_slots is None:
        faculty_busy_slots = {}
    if subject_faculty_map is None:
        subject_faculty_map = {}

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
        return [], []

    pool_counts = Counter(class_pool)
    total_needed = len(class_pool)
    time_idx_map = {t: i for i, t in enumerate(timeslots)}

    # High-priority subjects: those at or near the maximum priority
    max_p = max(priorities.values()) if priorities else 0
    high_priority_subjects = {s for s, p in priorities.items() if p >= max(1, max_p - 1)}

    # ═══════════════════════════════════════════════════════════════════════════
    # DECODE  — chromosome (ordering) → concrete schedule
    # ═══════════════════════════════════════════════════════════════════════════
    def decode(ordering: list[str], local_faculty_busy: dict):
        """
        Greedy decoder: assign each subject in chromosome order to the next
        available valid (day, timeslot) slot.

        Hard constraints enforced:
          1. No two subjects share the same (day, timeslot) within this class.
          2. No subject placed in a slot marked invalid for it (break slot).
          3. Max 2 lectures per subject per day.
          4. No lectures on blocked days.
          5. [NEW] Faculty hard constraint: check local_faculty_busy[teacher_id]
             before every assignment. Update it immediately on assignment.

        Args:
            ordering           : chromosome (list of subject names, ordered)
            local_faculty_busy : deepcopy of faculty_busy_slots for this evaluation.
                                 MUTATED locally — never touches global state.

        Returns:
            (schedule, unscheduled) tuple.
            schedule    = list of entry dicts
            unscheduled = list of {"subject": str, "reason": str}
        """
        schedule = []
        unscheduled = []
        slots = all_slots[:]          # Work on a copy; ordering is fixed
        subject_day_counts: dict = {}

        for subj in ordering:
            assigned = False
            # Break / legacy invalid slots for this subject
            break_constraints = invalid_slots.get(subj, set())
            # The faculty teaching this subject
            teacher_id = subject_faculty_map.get(subj)
            # Faculty's currently-busy slots (from cross-class occupancy + this decode)
            faculty_busy = local_faculty_busy.get(teacher_id, set()) if teacher_id else set()

            for i, (day, time) in enumerate(slots):
                # Hard constraint 1: max 2 lectures per subject per day
                if subject_day_counts.get((subj, day), 0) >= 2:
                    continue

                # Hard constraint 2: break/invalid slots
                if (day, time) in break_constraints:
                    continue

                # Hard constraint 3: FACULTY CONFLICT CHECK
                # If teacher is already occupied at (day, time) in ANY class, skip.
                if (day, time) in faculty_busy:
                    continue

                # All constraints satisfied — assign this slot
                schedule.append({"subject": subj, "day": day, "timeslot": time})
                slots.pop(i)
                subject_day_counts[(subj, day)] = (
                    subject_day_counts.get((subj, day), 0) + 1
                )
                # Update local faculty busy immediately so next lecture in same
                # decode pass cannot reuse this slot for the same teacher.
                if teacher_id is not None:
                    if teacher_id not in local_faculty_busy:
                        local_faculty_busy[teacher_id] = set()
                    local_faculty_busy[teacher_id].add((day, time))
                    faculty_busy = local_faculty_busy[teacher_id]

                assigned = True
                break

            if not assigned:
                unscheduled.append({
                    "subject": subj,
                    "reason": "No conflict-free slot available after applying faculty and timetable constraints"
                })

        return schedule, unscheduled

    # ═══════════════════════════════════════════════════════════════════════════
    # FITNESS FUNCTION
    # Each call to calculate_fitness gets its OWN deepcopy of faculty_busy_slots.
    # This is critical: without deepcopy, GA generations corrupt shared state.
    # ═══════════════════════════════════════════════════════════════════════════
    def calculate_fitness(ordering: list[str]) -> float:
        """
        Decode chromosome and score the resulting schedule.

        Uses deepcopy(faculty_busy_slots) so each evaluation is independent.

        Rewards:
          +100  per unique subject on a day (variety)
          +30   per subject per day (spreading across days)
          +2×p  per lecture (general priority reward, p = priority value)
          +20×p for each consecutive pair of high-priority lectures on same day
          +50   bonus per successfully scheduled lecture (conflict avoidance reward)

        Penalties:
          -500×(k-2) if a subject appears >2 times on same day (k = excess count)
          -20        if a non-high-priority subject has 2 lectures on same day
          -100×count if multi-lectures on same day are NOT in consecutive time slots
          -200       per unscheduled lecture (strong pressure toward full feasibility)
        """
        local_busy = deepcopy(faculty_busy_slots)
        schedule, unscheduled = decode(ordering, local_busy)

        if not schedule and unscheduled:
            return float("-inf")

        score = 0.0

        # Penalty for unscheduled lectures
        score -= len(unscheduled) * 200

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

                # General priority reward per lecture + scheduling success bonus
                score += priorities.get(subj, 1) * 2
                score += 50  # reward for each successfully placed lecture

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
    # DECODE BEST CHROMOSOME — final authoritative decode with fresh deepcopy
    # ═══════════════════════════════════════════════════════════════════════════
    if best_chromosome:
        final_busy = deepcopy(faculty_busy_slots)
        result_schedule, result_unscheduled = decode(best_chromosome, final_busy)
        if result_schedule:
            return result_schedule, result_unscheduled

    # Fallback: try each population member in case best chromosome decodes empty
    for ch in population:
        final_busy = deepcopy(faculty_busy_slots)
        result_schedule, result_unscheduled = decode(ch, final_busy)
        if result_schedule:
            return result_schedule, result_unscheduled

    return [], [{"subject": s, "reason": "No feasible schedule found after full GA run"} for s in class_pool]
