from typing import Any
from pysat.solvers import Minisat22
from pysat.formula import CNF, IDPool
from pysat.card import CardEnc

def gen_solution(durations: list[int], c: int, T: int) -> None | list[tuple]:
    """
    Variables:
    - A(i, t): poule i est côté A à l'instant t
    - B(i, t): poule i est côté B à l'instant t
    - Travel(t, d): voyage de durée d commence à l'instant t
    - TravelDir(t): direction du voyage (False=A->B, True=B->A)
    - OnBoard(i, t): poule i embarque au voyage commençant à t
    """
    from pysat.formula import CNFPlus, IDPool
    from pysat.card import CardEnc
    from pysat.solvers import Minicard

    n = len(durations)
    max_d = max(durations)

    cnf = CNFPlus()
    vpool = IDPool()

    # ---------- Variables ----------
    def A(i, t):
        return vpool.id(("A", i, t))

    def B(i, t):
        return vpool.id(("B", i, t))

    def Travel(t, d):
        return vpool.id(("Travel", t, d))  # Voyage de durée d commence à t

    def TravelDir(t):
        return vpool.id(("TravelDir", t))  # False=A->B, True=B->A

    def OnBoard(i, t):
        return vpool.id(("OnBoard", i, t))  # Poule i embarque voyage à t

    def BoatSide(t):
        return vpool.id(("BoatSide", t))  # False=A, True=B

    # ---------- État initial (t=0) ----------
    for i in range(n):
        cnf.append([A(i, 0)])  # Toutes les poules commencent côté A
        cnf.append([-B(i, 0)])

    cnf.append([-BoatSide(0)])  # Barque côté A au départ

    # ---------- État final (t=T) ----------
    for i in range(n):
        cnf.append([B(i, T)])  # Toutes les poules doivent être côté B
        cnf.append([-A(i, T)])

    # ---------- Contraintes de position: A et B sont exclusifs ----------
    for t in range(T + 1):
        for i in range(n):
            cnf.append([-A(i, t), -B(i, t)])  # Pas à la fois en A et B
            cnf.append([A(i, t), B(i, t)])  # Au moins à A ou B

    # ---------- Exactement un voyage par instant (ou aucun) ----------
    for t in range(T + 1):
        lits = [Travel(t, d) for d in range(max_d + 1)]
        cnf.extend(CardEnc.atmost(lits, 1, vpool=vpool))  # Au plus un voyage

    # ---------- Capacité de la barque ----------
    for t in range(T + 1):
        lits_onboard = [OnBoard(i, t) for i in range(n)]
        cnf.extend(CardEnc.atmost(lits_onboard, c, vpool=vpool))

    # ---------- Si voyage: au moins une poule embarque ----------
    for t in range(T + 1):
        for d in range(max_d + 1):
            lits_onboard = [OnBoard(i, t) for i in range(n)]
            # -Travel(t, d) OU (au moins 1 poule embarque)
            cnf.extend(CardEnc.atleast(lits_onboard, 1, vpool=vpool))
            # Implication simplifiée: Travel(t, d) -> (au moins une poule)
            for i in range(n):
                # Si Travel et pas cette poule, une autre doit embarquer
                pass

            cnf.append([-Travel(t, d)] + lits_onboard)

    # ---------- Embarquement cohérent ----------
    for t in range(T + 1):
        for d in range(max_d + 1):
            for i in range(n):
                # Embarquement A vers B: poule doit être en A et barque coté A
                cnf.append([-OnBoard(i, t), -Travel(t, d), -TravelDir(t), A(i, t)])

                # Embarquement B vers A: poule doit être en B et barque coté B
                cnf.append([-OnBoard(i, t), -Travel(t, d), TravelDir(t), B(i, t)])

    # ---------- Cohérence direction / position barque ----------
    for t in range(T + 1):
        for d in range(max_d + 1):
            if t + d <= T:
                # Si voyage A vers B: barque en A avant, en B après
                cnf.append([-Travel(t, d), -TravelDir(t), -BoatSide(t)])
                cnf.append([-Travel(t, d), -TravelDir(t), BoatSide(t + d)])

                # Si voyage B vers A: barque en B avant, en A après
                cnf.append([-Travel(t, d), TravelDir(t), BoatSide(t)])
                cnf.append([-Travel(t, d), TravelDir(t), -BoatSide(t + d)])

    # ---------- Durée du voyage = max des durées des poules embarquées ----------
    for t in range(T + 1):
        for d in range(max_d + 1):
            if t + d <= T:
                # Si voyage de durée d, au moins une poule a durée d
                lits_duration_d = []
                for i in range(n):
                    if durations[i] == d:
                        lits_duration_d.append(OnBoard(i, t))

                if lits_duration_d:
                    cnf.append([-Travel(t, d)] + lits_duration_d)

                # Si voyage de durée d, pas de poule avec durée > d
                for i in range(n):
                    if durations[i] > d:
                        cnf.append([-Travel(t, d), -OnBoard(i, t)])

    # ---------- Mise à jour positions après un voyage ----------
    for t in range(T + 1):
        for d in range(max_d + 1):
            if t + d <= T:
                for i in range(n):
                    # Embarquement A->B
                    cnf.append([-OnBoard(i, t), -Travel(t, d), -TravelDir(t), B(i, t + d)])

                    # Embarquement B->A
                    cnf.append([-OnBoard(i, t), -Travel(t, d), TravelDir(t), A(i, t + d)])

    # ---------- Persistance: poules qui n'embarquent pas conservent position ----------
    for t in range(T + 1):
        for d in range(max_d + 1):
            if t + d <= T:
                for i in range(n):
                    # Pas embarquement A vers B: conserve position
                    cnf.append([-Travel(t, d), -TravelDir(t), OnBoard(i, t), A(i, t + d)])
                    cnf.append([-Travel(t, d), -TravelDir(t), -A(i, t), -A(i, t + d)])

                    # Pas embarquement B vers A: conserve position
                    cnf.append([-Travel(t, d), TravelDir(t), OnBoard(i, t), B(i, t + d)])
                    cnf.append([-Travel(t, d), TravelDir(t), -B(i, t), -B(i, t + d)])

    # ---------- Persistance de la barque entre les voyages ----------
    for t in range(T):
        for d in range(1, max_d + 1):
            if t + d <= T:
                # S'il y a voyage de t à t+d, barque reste stable après
                for t_inter in range(t + 1, t + d):
                    if t_inter <= T:
                        cnf.append([-Travel(t, d), BoatSide(t + d)])

    # ---------- Persistance positions entre instants sans voyage ----------
    for t in range(T):
        for d in range(1, max_d + 1):
            if t + d <= T:
                for i in range(n):
                    for t_inter in range(t + 1, t + d):
                        if t_inter <= T:
                            cnf.append([-Travel(t, d), A(i, t), A(i, t_inter)])
                            cnf.append([-Travel(t, d), B(i, t), B(i, t_inter)])

    # ---------- Résolution ----------
    solver = Minicard()
    solver.append_formula(cnf.clauses)

    if not solver.solve():
        return None

    model = set(solver.get_model())

    # ---------- Construction de la solution ----------
    result = []

    for t in range(T + 1):
        # Chercher si un voyage commence à cet instant
        for d in range(max_d + 1):
            if Travel(t, d) in model:
                chickens = []
                for i in range(n):
                    if OnBoard(i, t) in model:
                        chickens.append(i + 1)

                direction = "AversB" if TravelDir(t) not in model else "BversA"
                result.append((t, chickens, d, direction))
                break

    return result


def find_duration(durations: list[int], c: int) -> int:
    """
    Trouve la durée minimale pour transporter toutes les poules
    Recherche binaire sur T
    """
    # Borne min
    min_T = max(durations)

    # Borne max
    max_T = sum(durations) * 2

    best_T = None

    while min_T <= max_T:
        mid_T = (min_T + max_T) // 2
        solution = gen_solution(durations, c, mid_T)

        if solution is not None:
            best_T = mid_T
            max_T = mid_T - 1
        else:
            min_T = mid_T + 1
    return best_T


def find_duration(durations: list[int], c: int) -> int:
    pass


# Local test

res = gen_solution([1, 3, 6, 8], 2, 18)

if res == [(0, [1, 2]), (3, [1]), (4, [3, 4]), (12, [2]), (15, [1, 2])]:
    print("Test passed!")
else:
    print("Test failed")
