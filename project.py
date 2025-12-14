from typing import Any
from pysat.solvers import Minisat22
from pysat.formula import CNF, IDPool
from pysat.card import CardEnc

def gen_solution(durations: list[int], c: int, T: int) -> None | list[tuple]:
    N = len(durations)
    solution_display = True
    vpool = IDPool(start_from=1)
    directions = ["aller", "retour"]
    cnf = CNF()

    # ----------Définition des variables

    def A(p: int, t: int) -> (int | Any): return vpool.id(("A", p, t))
    def B(p: int, t: int) -> (int | Any): return vpool.id(("B", p, t))
    def side(t: int) -> (int | Any): return vpool.id(("side", t))
    def dep(t: int, p: int, s: str) -> (int | Any): return vpool.id(("dep", t, p, s))
    def dur(t: int, d: int) -> (int | Any): return vpool.id(("dur", t, d))
    def Dep(t: int) -> (int | Any): return vpool.id(("Dep", t))
    def Arr(t: int) -> (int | Any): return vpool.id(("Arr", t))
    def AllB(t: int) -> (int | Any): return vpool.id(("AllB", t))
    
    # ----------Construction des clauses----------

    # Conditions initiales:
    #   Toutes les poules en A
    #   Bateau en A
    for p in range(N):
        cnf.append([A(p, 0)])
    cnf.append([-side(0)])

    # Conditions finales
    #   Toutes les poules en B
    #   Bateau en B
    for p in range(N):
        cnf.append([B(p, T)])
    cnf.append([side(T)])

    # ----------Résolution----------

    res = []
    solver = Minisat22(use_timer=True)
    solver.append_formula(cnf.clauses, no_return=False)

    print("Resolution...")
    result = solver.solve()
    print("Problème satisfaisable : " + str(result))

    print("Temps de resolution : " + '{0:.2f}s'.format(solver.time()))

    # Affichage de la solution
    res_model = solver.get_model()

    if solution_display and result:

        print("Voici une solution: \n")

        for t in range(T + 1):
            for p in range(N):
                for s in directions:
                    chickens = []
                    if vpool.id(("dep", t, p, s)) in res_model:
                        chickens.append(p + 1)

            if len(chickens) > 0:
                res.append((t, chickens))

        print(res)
        return res
    else:
        return None


def find_duration(durations: list[int], c: int) -> int:
    pass


# Local test

res = gen_solution([1, 3, 6, 8], 2, 18)

if res == [(0, [1, 2]), (3, [1]), (4, [3, 4]), (12, [2]), (15, [1, 2])]:
    print("Test passed!")
else:
    print("Test failed")
