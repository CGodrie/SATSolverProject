def gen_solution(durations: list[int], c: int, T: int) -> None | list[tuple]:
    from pysat.formula import CNFPlus
    from pysat.card import CardEnc
    from pysat.solvers import Minicard

    n = len(durations)
    max_d = max(durations)

    cnf = CNFPlus()
    vpool = cnf.vpool

    # ---------- variable ----------
    def A(i, t): return vpool.id(("A", i, t))
    def B(i, t): return vpool.id(("B", i, t))

    def Go(t): return vpool.id(("Go", t))
    def Back(t): return vpool.id(("Back", t))

    def OnAB(i, t): return vpool.id(("OnAB", i, t))
    def OnBA(i, t): return vpool.id(("OnBA", i, t))

    def Dur(t, d): return vpool.id(("Dur", t, d))
    def Side(t): return vpool.id(("Side", t))

    # ---------- État initial ----------
    for i in range(n):
        cnf.append([A(i, 0)])   # A(i,0) = True
        cnf.append([-B(i, 0)])  # B(i,0) = False

    cnf.append([-Side(0)])  # Side(0) = False (barque côté A)

    # ---------- Etat final ----------
    for i in range(n):
        cnf.append([B(i, T)])

    # ---------- Un seul sens par instant ----------
    for t in range(T + 1):
        cnf.append([-Go(t), -Back(t)])

    # ---------- Capacite barque ----------
    for t in range(T + 1):
        lits_AB = [OnAB(i, t) for i in range(n)]
        lits_BA = [OnBA(i, t) for i in range(n)]
        cnf.extend(CardEnc.atmost(lits_AB, c, vpool=vpool))
        cnf.extend(CardEnc.atmost(lits_BA, c, vpool=vpool))

    # ---------- Coherence barque / direction ----------
    for t in range(T + 1):
        cnf.append([-Go(t), -Side(t)])   # Go(t) -> barque côté A
        cnf.append([-Back(t), Side(t)])  # Back(t) -> barque côté B

    # ---------- Embarquement coherent ----------
    for t in range(T + 1):
        for i in range(n):
            cnf.append([-OnAB(i, t), A(i, t)])   # OnAB -> poule sur A
            cnf.append([-OnBA(i, t), B(i, t)])   # OnBA -> poule sur B

    # ---------- Duree : un voyage => une durée ----------
    for t in range(T + 1):
        cnf.append([-Go(t)] + [Dur(t, d) for d in range(max_d + 1)])
        cnf.append([-Back(t)] + [Dur(t, d) for d in range(max_d + 1)])

    # ---------- Duree : aucune poule trop lente ----------
    for t in range(T + 1):
        for d in range(max_d + 1):
            for i in range(n):
                if durations[i] > d:
                    cnf.append([-Dur(t, d), -OnAB(i, t)])
                    cnf.append([-Dur(t, d), -OnBA(i, t)])

    # ---------- Duree : au moins une poule de duree exacte ----------
    for t in range(T + 1):
        for d in range(max_d + 1):
            lits = []
            for i in range(n):
                if durations[i] == d:
                    lits.append(OnAB(i, t))
                    lits.append(OnBA(i, t))
            if lits:
                cnf.append([-Dur(t, d)] + lits)

    # ---------- Mise a jour cote barque ----------
    for t in range(T + 1):
        for d in range(max_d + 1):
            if t + d <= T:
                cnf.append([-Go(t), -Dur(t, d), Side(t + d)])
                cnf.append([-Back(t), -Dur(t, d), -Side(t + d)])

    # ---------- Mise a jour positions poules ----------
    for t in range(T + 1):
        for d in range(max_d + 1):
            if t + d <= T:
                for i in range(n):
                    cnf.append([-OnAB(i, t), -Dur(t, d), B(i, t + d)])
                    cnf.append([-OnBA(i, t), -Dur(t, d), A(i, t + d)])

    # ---------- Résolution ----------
    solver = Minicard()
    solver.append_formula(cnf.clauses)

    if not solver.solve():
        return None

    model = set(solver.get_model())

    # ---------- Build solution ----------
    result = []

    for t in range(T + 1):
        if Go(t) in model or Back(t) in model:
            chickens = []
            for i in range(n):
                if OnAB(i, t) in model or OnBA(i, t) in model:
                    chickens.append(i + 1)
            result.append((t, chickens))

    return result

def find_duration(durations: list[int], c: int) -> int:
    pass
