import os
import time
import pandas as pd

from ls_swap_FirstANDMixed import (
    read_instance,
    construct_solution,
    precompute_offsets,
    local_search_first_improvement,
    local_search_mixed_improvement,
    evaluate_sequence_preciso,
    INSTANCES,
    INSTANCES_DIR
)

# ─────────────────────────────────────────────
# PARÁMETROS EXPERIMENTO
# ─────────────────────────────────────────────
LB_FILE = "lb.txt"

# Valores de R a testear
MIXED_R_VALUES = [0.1, 0.2, 0.4, 0.6, 0.8]

OUTPUT_FILE = "resultados\\experiment_swap.csv"

TIME_LIMIT_GLOBAL = 3600


# ─────────────────────────────────────────────
# LEER COTAS INFERIORES
# ─────────────────────────────────────────────
def read_LB(file):
    with open(file) as f:
        lbs = [float(line.strip()) for line in f if line.strip()]
    return lbs


# ─────────────────────────────────────────────
# EXPERIMENTO
# ─────────────────────────────────────────────
def run_experiment():
    lbs = read_LB(LB_FILE)

    results = []

    for idx, inst in enumerate(INSTANCES):

        filepath = os.path.join(INSTANCES_DIR, inst)

        if not os.path.exists(filepath):
            print(f"[SKIP] {inst}")
            continue

        if idx >= len(lbs):
            print(f"[SKIP LB] No hay LB para {inst}")
            continue

        LB = lbs[idx]

        print(f"\n==============================")
        print(f"Instancia: {inst}")
        print(f"LB: {LB}")
        print(f"==============================")

        # Leer instancia
        jobs, m = read_instance(filepath)
        offsets_list = precompute_offsets(jobs)

        # Tiempo global
        t0 = time.time()

        # ─────────────
        # NEH
        # ─────────────
        sequence = construct_solution(jobs, m)

        # ─────────────
        # FIRST IMPROVEMENT (una sola vez)
        # ─────────────
        seq_first, z_first, t_first = local_search_first_improvement(
            sequence, jobs, m, offsets_list, t0
        )

        gap_first = (z_first - LB) / LB

        results.append({
            "algoritmo": "FirstImprovement",
            "instancia": inst,
            "R": None,
            "Z": z_first,
            "LB": LB,
            "GAP": gap_first
        })

        print(f"[FIRST] Z={z_first} GAP={gap_first:.4f}")

        # ─────────────
        # MIXED PARA VARIOS R
        # ─────────────
        for R in MIXED_R_VALUES:

            # reiniciar tiempo para fairness (opcional)
            t_start = time.time()

            seq_mixed, z_mixed, _ = local_search_mixed_improvement(
                sequence, jobs, m, offsets_list, t_start, R
            )

            gap_mixed = (z_mixed - LB) / LB

            results.append({
                "algoritmo": "MixedImprovement",
                "instancia": inst,
                "R": R,
                "Z": z_mixed,
                "LB": LB,
                "GAP": gap_mixed
            })

            print(f"[MIXED R={R}] Z={z_mixed} GAP={gap_mixed:.4f}")

    return results


# ─────────────────────────────────────────────
# GUARDAR RESULTADOS
# ─────────────────────────────────────────────
def save_results(results):
    df = pd.DataFrame(results)

    # Orden bonito
    df = df.sort_values(by=["instancia", "algoritmo", "R"])

    os.makedirs(os.path.dirname(OUTPUT_FILE) if os.path.dirname(OUTPUT_FILE) else ".", exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)

    print(f"\nResultados guardados en: {OUTPUT_FILE}")

    # Vista tipo tabla para informe
    print("\n=== TABLA RESUMEN ===")
    print(df.to_string(index=True))


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import random
    random.seed(42)
    results = run_experiment()
    save_results(results)