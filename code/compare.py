import os
import pandas as pd

# ─────────────────────────────────────────────
# CONFIGURACIÓN (sin cambios)
# ─────────────────────────────────────────────

INSTANCES = [
    "ft06.txt", "ft06r.txt",
    "ft10.txt", "ft10r.txt",
    "ft20.txt", "ft20r.txt",
    "tai_j10_m10_1.txt", "tai_j10_m10_1r.txt",
    "tai_j100_m10_1.txt", "tai_j100_m10_1r.txt",
    "tai_j100_m100_1.txt", "tai_j100_m100_1r.txt",
    "tai_j1000_m10_1.txt", "tai_j1000_m10_1r.txt",
]

FILES = {
    "Swap-FI":    "NWJSSP_OADG_NEH(SwapFirstImprovement).xlsx",
    "Swap-M":     "NWJSSP_OADG_NEH(SwapMixedImprovement).xlsx",
    "InsUP-FI":   "NWJSSP_OADG_NEH(InsertionUPFirstImprovement).xlsx",
    "InsUP-M":    "NWJSSP_OADG_NEH(InsertionUPMixedImprovement).xlsx",
    "InsDOWN-FI": "NWJSSP_OADG_NEH(InsertionDOWNFirstImprovement).xlsx",
    "InsDOWN-M":  "NWJSSP_OADG_NEH(InsertionDOWNMixedImprovement).xlsx",
}

LB_FILE = "lb.txt"
RESULTS_DIR = "resultados"
OUTPUT_CSV = os.path.join(RESULTS_DIR, "GAP_table.csv")

# ─────────────────────────────────────────────
# LECTURA DE LAS COTAS INFERIORES (sin cambios)
# ─────────────────────────────────────────────

def read_lb(lb_file, instances):
    with open(lb_file, "r") as f:
        lb_values = [float(line.strip()) for line in f if line.strip()]

    if len(lb_values) < len(instances):
        raise ValueError("lb.txt no tiene suficientes cotas para las instancias solicitadas")

    return dict(zip(instances, lb_values[:len(instances)]))

# ─────────────────────────────────────────────
# LECTURA DE Z DESDE EXCEL (sin cambios)
# ─────────────────────────────────────────────

def read_z_from_excel(excel_path, instance_name):
    sheet_name = instance_name.replace(".txt", "")
    try:
        df = pd.read_excel(excel_path, sheet_name=sheet_name, header=None)
        return float(df.iloc[0, 0])
    except Exception:
        return None

# ─────────────────────────────────────────────
# MAIN - SOLO CAMBIO AQUÍ
# ─────────────────────────────────────────────

def main():
    lb_dict = read_lb(LB_FILE, INSTANCES)

    # Creamos el DataFrame con instancias como filas
    table = pd.DataFrame(index=[inst.replace(".txt", "") for inst in INSTANCES])

    for alg_name, excel_file in FILES.items():
        excel_path = os.path.join(RESULTS_DIR, excel_file)

        if not os.path.exists(excel_path):
            print(f"[WARNING] No existe: {excel_path}")
            continue

        gaps = []
        for inst in INSTANCES:
            lb = lb_dict[inst]
            z = read_z_from_excel(excel_path, inst)

            if z is None:
                gap = float("nan")
            else:
                gap = (z - lb) / lb

            gaps.append(gap)

        table[alg_name] = gaps

    # Convertir a numérico
    table = table.apply(pd.to_numeric, errors="coerce")

    # === CAMBIO PRINCIPAL: Calcular promedios por columna ===
    avg_row = table.mean(axis=0, skipna=True)
    avg_row.name = "GAP promedio"

    # Añadir la fila de promedios al final
    table = pd.concat([table, avg_row.to_frame().T])

    # ─────────────────────────────────────────────
    # IMPRESIÓN EN CONSOLA
    # ─────────────────────────────────────────────

    print("\n================= GAP TABLE =================")
    format_table = table.copy()
    for col in format_table.columns:
        format_table[col] = format_table[col].apply(
            lambda x: f"{x:.6f}" if pd.notnull(x) else "NA"
        )

    print(format_table.to_string())
    print("============================================\n")

    # ─────────────────────────────────────────────
    # GUARDADO CSV (con la fila de promedios incluida)
    # ─────────────────────────────────────────────

    os.makedirs(RESULTS_DIR, exist_ok=True)
    table.to_csv(OUTPUT_CSV, float_format="%.8f")

    print(f"Tabla guardada en: {OUTPUT_CSV}")

# ─────────────────────────────────────────────

if __name__ == "__main__":
    main()