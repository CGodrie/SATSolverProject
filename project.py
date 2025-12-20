"""
Retourne None s'il n'existe pas de solution pour un temps <= T,
sinon une liste de tuples [(t, [poules])] représentant les départs des poules.
"""
def gen_solution(durations: list[int], c: int, T: int) -> None | list[tuple]:
    """
    Variables:
    - A(p, t): vraie ssi la poule p est sur la berge A à l'instant t
    - dur(t, d): vraie ssi un voyage de durée d commence à l'instant t
    - DEP(t): vraie ssi il y a un départ à l'instant t
    - dep(t, p): vraie ssi la poule p embarque au voyage commençant à t
    - ARR(t): vraie ssi il y a une arrivée sur une berge à l'instant t
    - move(p, t): vraie ssi la poule p débarque à l'instant t
    - side(t): vraie ssi la barque est sur la berge A à l'instant t
    - ALLATB(t): vraie ssi toutes les poules sont sur la berge B à l'instant T
    """
    from pysat.formula import CNF, IDPool
    from pysat.card import CardEnc
    from pysat.solvers import Minisat22

    n = len(durations)
    maxT = max(durations)

    if n == 0:
        print("Pas de poules, solution vide")
        return []
    if c <= 0 or T < 0:
        print("Paramètres rendant impossible la satisfaisabilité du problème")
        return None

    vpool = IDPool()
    cnf = CNF()

    # ---------- Variables ----------
    
    def A(p: int, t: int) -> int:
        return vpool.id(("A", p, t))        # True => poule p sur berge A à t (sinon B)

    def side(t: int) -> int:
        return vpool.id(("side", t))        # True => barque côté A à t (sinon B)

    def dep(t: int, p: int) -> int:
        return vpool.id(("dep", t, p))      # True => poule p embarquée au départ t

    def DEP(t: int) -> int:
        return vpool.id(("DEP", t))         # True => départ à t

    def dur(t: int, d: int) -> int:
        return vpool.id(("dur", t, d))      # True => durée d du voyage à t (d=0 <-> pas de départ)

    def ARR(t: int) -> int:
        return vpool.id(("ARR", t))         # True => arrivée à t

    def move(t: int, p: int) -> int:
        return vpool.id(("move", t, p))     # True => poule p arrive à t (donc change de berge à t)

    def ALL(t: int) -> int:
        return vpool.id(("ALL", t))         # True => toutes les poules sur B à t
    
    # ---------- Variables Auxiliaires ----------

    def link(t0: int, d: int, p: int) -> int:
        # link(t0,d,p) <-> dep(t0,p) & dur(t0,d)
        return vpool.id(("link", t0, d, p)) # True => départ à t et durée d pour le voyage

    # -----------------------------
    # Helpers CNF
    # -----------------------------
    def add_imp(a: int, b: int) -> None:
        cnf.append([-a, b])

    def add_equiv(a: int, b: int) -> None:
        add_imp(a, b)
        add_imp(b, a)

    # -----------------------------
    # 1) Initialisation
    # -----------------------------
    for p in range(1, n + 1):
        cnf.append([A(p, 0)])  # toutes sur A au temps 0
    cnf.append([side(0)])  # barque sur A au temps 0

    # -----------------------------
    # 2) ALL(t) <-> (toutes sur B)
    #    ALL(t) -> ¬A(p,t) pour tout p
    #    (∀p ¬A(p,t)) -> ALL(t) équiv à (A(1,t) ∨ A(2,t) ∨ ... ∨ ALL(t))
    # -----------------------------
    for t in range(0, T + 1):
        for p in range(1, n + 1):
            cnf.append([-ALL(t), -A(p, t)])
        cnf.append([ALL(t)] + [A(p, t) for p in range(1, n + 1)])

    # -----------------------------
    # 3) DEP(t) <-> OR dep(t,p), capacité ≤ c
    #    et on interdit DEP(T) (pas de temps pour terminer)
    # -----------------------------
    for t in range(0, T + 1):
        dep_lits = [dep(t, p) for p in range(1, n + 1)]

        # dep(t,p) -> DEP(t)
        for lit in dep_lits:
            add_imp(lit, DEP(t))

        # DEP(t) -> OR dep(t,p)
        cnf.append([-DEP(t)] + dep_lits)

        # capacité: au plus C poules
        cnf.extend(CardEnc.atmost(dep_lits, bound=c, vpool=vpool, encoding=1).clauses)

        if t == T:
            cnf.append([-DEP(t)])
            for p in range(1, n + 1):
                cnf.append([-dep(t, p)])

    # -----------------------------
    # 4) dur(t,d): exactly one d in 0..maxT
    #    dur(t,0) <-> ¬DEP(t)
    #    et d>0 impossible si t+d>T
    # -----------------------------
    for t in range(0, T + 1):

        # exactement une durée à chaque instant
        d_lits = [dur(t, d) for d in range(0, maxT + 1)]
        cnf.extend(CardEnc.equals(d_lits, bound=1, vpool=vpool, encoding=1).clauses)

        # pas de durée (d = 0) <-> pas de départ
        cnf.append([-dur(t, 0), -DEP(t)])
        cnf.append([DEP(t), dur(t, 0)])

        # pas de durée faisant dépasser du temps alloué
        for d in range(1, maxT + 1):
            if t + d > T:
                cnf.append([-dur(t, d)])

    # -----------------------------
    # 5) Durée = max(Ti) des poules embarquées
    #    dur(t,d) -> (aucune embarquée avec Ti>d) et (au moins une avec Ti=d)
    # -----------------------------
    for t in range(0, T):
        for d in range(1, maxT + 1):
            # aucune embarquée avec Ti>d
            for p in range(1, n + 1):
                if durations[p - 1] > d:
                    cnf.append([-dur(t, d), -dep(t, p)])

            # au moins une embarquée avec Ti=d
            eq_ps = [dep(t, p) for p in range(1, n + 1) if durations[p - 1] == d]
            if not eq_ps:
                cnf.append([-dur(t, d)])
            else:
                cnf.append([-dur(t, d)] + eq_ps)

        # embarquer p implique une durée >= Ti
        for p in range(1, n + 1):
            Ti = durations[p - 1]
            cnf.append([-dep(t, p)] + [dur(t, d) for d in range(Ti, maxT + 1)])

    # -----------------------------
    # 6) Cohérence "côté" au départ: on embarque seulement depuis la bonne berge
    # -----------------------------
    for t in range(0, T):
        for p in range(1, n + 1):
            # side(t)=A & dep(t,p) -> A(p,t)
            cnf.append([-side(t), -dep(t, p), A(p, t)])
            # side(t)=B & dep(t,p) -> ¬A(p,t)
            cnf.append([side(t), -dep(t, p), -A(p, t)])

    # -----------------------------
    # 7) Interdiction de départ pendant une traversée
    # -----------------------------
    for t in range(0, T):
        for d in range(1, maxT + 1):
            if t + d > T:
                continue
            for tp in range(t + 1, t + d):
                cnf.append([-dur(t, d), -DEP(tp)])

    # -----------------------------
    # 8) ARR : EXACTEMENT les temps qui sont t0+d pour un départ t0 de durée d
    #    - dur(t0,d) -> ARR(t0+d)
    #    - ARR(t) -> OR_{t0< t} dur(t0, t-t0)
    # -----------------------------
    cnf.append([-ARR(0)])  # pas d'arrivée à t=0
    for t0 in range(0, T):
        for d in range(1, maxT + 1):
            t_arr = t0 + d
            if t_arr <= T:
                add_imp(dur(t0, d), ARR(t_arr))

    for t in range(1, T + 1):
        possible = []
        for t0 in range(0, t):
            d = t - t0
            if 1 <= d <= maxT:
                possible.append(dur(t0, d))
        if possible:
            cnf.append([-ARR(t)] + possible)
        else:
            cnf.append([-ARR(t)])

    # "timeline compacte" (utile pour matcher les tests): après une arrivée, si pas fini, on repart immédiatement
    # et tout départ t>0 doit être à une arrivée.
    cnf.append([ALL(0), DEP(0)])  # si pas fini à 0, départ à 0
    for t in range(1, T + 1):
        add_imp(DEP(t), ARR(t))
        if t < T:
            cnf.append([-ARR(t), ALL(t), DEP(t)])  # ARR(t) & ¬ALL(t) -> DEP(t)

    # -----------------------------
    # 9) side(t) : toggle à chaque ARR(t), sinon stable
    # -----------------------------
    for t in range(1, T + 1):
        # si ARR(t): side(t)!=side(t-1)
        cnf.append([-ARR(t), -side(t), -side(t - 1)])
        cnf.append([-ARR(t), side(t), side(t - 1)])
        # si ¬ARR(t): side(t)==side(t-1)
        cnf.append([ARR(t), -side(t), side(t - 1)])
        cnf.append([ARR(t), -side(t - 1), side(t)])

    # -----------------------------
    # 10) move(t,p) : EXACTEMENT les poules embarquées au départ correspondant
    #     link(t0,d,p) <-> dep(t0,p) & dur(t0,d)
    #     move(t,p) <-> OR_{t0<t} link(t0, t-t0, p)
    #     puis évolution des berges:
    #       - si ¬ARR(t): A(p,t)=A(p,t-1)
    #       - si ARR(t): toggle ssi move(t,p)
    # -----------------------------
    for t0 in range(0, T):
        for d in range(1, maxT + 1):
            t_arr = t0 + d
            if t_arr > T:
                continue
            for p in range(1, n + 1):
                L = link(t0, d, p)
                # L -> dep and L -> dur
                cnf.append([-L, dep(t0, p)])
                cnf.append([-L, dur(t0, d)])
                # dep & dur -> L
                cnf.append([-dep(t0, p), -dur(t0, d), L])

    for t in range(1, T + 1):
        for p in range(1, n + 1):
            ors = []
            for t0 in range(0, t):
                d = t - t0
                if 1 <= d <= maxT:
                    ors.append(link(t0, d, p))

            # move -> OR links
            if ors:
                cnf.append([-move(t, p)] + ors)
            else:
                cnf.append([-move(t, p)])

            # OR links -> move
            for L in ors:
                cnf.append([-L, move(t, p)])

            # évolution A
            # si ¬ARR(t): A(p,t)==A(p,t-1)
            cnf.append([ARR(t), -A(p, t), A(p, t - 1)])
            cnf.append([ARR(t), -A(p, t - 1), A(p, t)])

            # si ARR(t) & move(t,p): toggle
            cnf.append([-ARR(t), -move(t, p), -A(p, t), -A(p, t - 1)])
            cnf.append([-ARR(t), -move(t, p),  A(p, t),  A(p, t - 1)])

            # si ARR(t) & ¬move(t,p): stable
            cnf.append([-ARR(t), move(t, p), -A(p, t),  A(p, t - 1)])
            cnf.append([-ARR(t), move(t, p),  A(p, t), -A(p, t - 1)])

    # -----------------------------
    # 11) Objectif : toutes sur B à T
    # -----------------------------
    cnf.append([ALL(T)])

    # ---------- Résolution ----------

    solver = Minisat22()
    solver.append_formula(cnf.clauses)

    if not solver.solve():
        return None

    model = solver.get_model()

    # ---------- Construction de la solution ----------

    result = []

    for t in range(T):
        if DEP(t) in model:
            passengers = [p for p in range(n + 1) if dep(t, p) in model]
            if len(passengers) != 0:
                result.append((t, passengers))

    return result


def find_duration(durations: list[int], c: int) -> int:
    """
    Renvoie le T minimal tel que gen_solution(durations, c, T) n'est pas None.
    """
    n = len(durations)

    if n == 0:
        return 0
    if c <= 0:
        return 0
    
    lower_limit = max(durations)
    upper_limit = 2 * sum(durations) - min(durations)

    for T in range(lower_limit, upper_limit + 1):
        if gen_solution(durations, c, T) is not None:
            return T

    return upper_limit