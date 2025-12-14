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

    # Expressions de Dep, Arr, et AllB en fonction des autres variables

    # 1. Un départ a lieu si et seulement si au moins une poule embarque
    #    Sens Dep => dep
    for t in range(T):
        lits_at_least_one_chicken = [-Dep(t)]
        for p in range(N):
            for s in directions:
                lits_at_least_one_chicken.append(dep(t, p, s))
        cnf.append(lits_at_least_one_chicken)

    #    Sens dep => Dep
    for t in range(T):
        for p in range(N):
            for s in directions:
                cnf.append([-dep(t, p, s), Dep(t)])

    # 2. La barque termine un voyage à un instant donné s'il y a eu un départ auparavant
    #    Une durée implique une arrivée
    for t in range(T):
        for d in durations:
            if t + d <= T:
                cnf.append([-dur(t, d), Arr(t + d)])
    
    #    Une arrivée implique une durée
    for arrival_time in range(T+1):
        lits_possible_durations = [-Arr(t)]
        for d in durations:
            if arrival_time - d >= 0:
                lits_possible_durations.append(dur(arrival_time - d, d))
        cnf.append(lits_possible_durations)

    # 3. AllB est vraie si et seulement si toutes les poules sont en B en même temps
    #    Sens AllB => B
    for t in range(T+1):
        for p in range(N):
            cnf.append([-AllB(t), B(p, t)])

    #    Sens B pour tout p => AllB
    for t in range(T+1):
        lits_all_b = []
        for p in range(N):
            lits_all_b.append(-B(p, t))
        lits_all_b.append(AllB(t))
        cnf.append(lits_all_b)

    # Contraintes liées à la durée des trajets

    # 1. Au plus une durée par voyage
    for t in range(T):
        for i1 in range(len(durations)):
            for i2 in range(len(durations)):
                if i1 != i2:
                    cnf.append([-dur(t, durations[i1]), -dur(t, durations[i2])])

    # 2. Si un voyage dure d, il y a au moins une poule à bord de même lenteur
    for t in range(T):
        for d in durations:
            lits_d_slow_chickens = [-dur(t, d)]
            for p in range(N):
                for s in directions:
                    if durations[p] == d:
                        lits_d_slow_chickens.append(dep(t, p, s))
            cnf.append(lits_d_slow_chickens)
    
    # 3. Si un voyage dure d, il n'y a aucune poule à bord plus lente
    for t in range(T):
        for d in durations:
            for p in range(N):
                for s in directions:
                    if durations[p] > d:
                        cnf.append([-dur(t, d), -dep(t, p, s)])

    # 4. Aucune poule ne peut embarquer pendant la durée d'un trajet (pas de départ possible)
    for t in range(T):
        for d in durations:
            if t + d <= T:
                for tprime in range(t + 1, t + d):
                    for p in range(N):
                        for s in directions:
                            cnf.append([-dur(t, d), -dep(tprime, p, s)])

    # Contraintes sur l'évolution de la population des poules

    # 1. Une poule ne peut pas être sur les deux berges au même moment
    for t in range(T+1):
        for p in range(N):
            cnf.append([-A(p, t), -B(p, t)])

    # 2. Une poule qui embarque pour un aller se retrouve sur la berge B
    for t in range(T):
        for p in range(N):
            for d in durations:
                if t + d <= T:
                    cnf.append([-dep(t, p, "aller"), -dur(t, d), B(p, t + d)])

    # 3. Une poule qui embarque pour un retour se retrouve sur la berge A
    for t in range(T):
        for p in range(N):
            for d in durations:
                if t + d < T:
                    cnf.append([-dep(t, p, "retour"), -dur(t, d), A(p, t + d)])

    # 4. Une poule qui ne voyage pas reste sur sa berge
    for t in range(T):
        for p in range(N):
            for d in durations:
                for s in directions:
                    if t + d <= T:
                        for tprime in range(t + 1, t + d):
                            cnf.append([-dur(t, d), dep(t, p, s), -A(p, t), A(p, tprime)])
                            cnf.append([-dur(t, d), dep(t, p, s), -B(p, t), B(p, tprime)])

    # 5. Au plus C poules par trajet
    for t in range(T):
        for s in directions:
            lits_max_c_chickens = []
            for p in range(N):
                lits_max_c_chickens.append(dep(t, p, s))
            cnf.extend(CardEnc.atmost(lits=lits_max_c_chickens, bound=c, vpool=vpool).clauses)
                
                

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
