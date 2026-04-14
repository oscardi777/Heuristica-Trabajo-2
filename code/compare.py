import os
import pandas as pd

# ─────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────
RESULTS_DIR = "resultados"

FILES = {
    "Swap-FI": "NWJSSP_OADG_NEH(SwapFirstImprovement).xlsx",
    "Swap-M":  "NWJSSP_OADG_NEH(SwapMixedImprovement).xlsx",
    "Ins-FI":  "NWJSSP_OADG_NEH(InsertionFirstImprovement).xlsx",
    "Ins-M":   "NWJSSP_OADG_NEH(InsertionMixedImprovement).xlsx"
}

LB_FILE = "lb.txt"


# ─────────────────────────────────────────────
# LEER LB (lista)
# ─────────────────────────────────────────────
def read_lb_list(file):
    lb_list = []
    with open(file) as f:
        for line in f:
            line = line.strip()
            if line:
                lb_list.append(float(line))
    return lb_list


# ─────────────────────────────────────────────
# LEER EXCEL (tolerante a errores)
# ─────────────────────────────────────────────
def read_results(file_path):
    results = {}

    if not os.path.exists(file_path):
        print(f"[WARNING] No existe: {file_path}")
        return results

    try:
        xls = pd.ExcelFile(file_path)
    except Exception as e:
        print(f"[ERROR] No se pudo abrir {file_path}: {e}")
        return results

    for sheet in xls.sheet_names:
        try:
            df = pd.read_excel(xls, sheet_name=sheet, header=None)

            Z = float(df.iloc[0, 0])
            tc = float(df.iloc[0, 1])

            results[sheet] = (Z, tc)

        except Exception as e:
            print(f"[WARNING] Error leyendo hoja {sheet} en {file_path}: {e}")
            continue

    return results


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():

    # Leer LB
    lb_list = read_lb_list(LB_FILE)

    # Leer todos los resultados
    all_results = {}
    for method, file in FILES.items():
        path = os.path.join(RESULTS_DIR, file)
        all_results[method] = read_results(path)

    # ─────────────────────────────────────────
    # Obtener TODAS las instancias disponibles
    # ─────────────────────────────────────────
    all_instances = set()
    for method in all_results:
        all_instances.update(all_results[method].keys())

    instances = sorted(list(all_instances))

    if len(instances) == 0:
        print("❌ No hay instancias encontradas en los Excel")
        return

    # ⚠️ Solo usamos tantas instancias como LB tengamos
    usable_n = min(len(instances), len(lb_list))

    if len(lb_list) < len(instances):
        print(f"[WARNING] Hay más instancias ({len(instances)}) que LB ({len(lb_list)}). Se recortará.")

    instances = instances[:usable_n]

    # ─────────────────────────────────────────
    # CONSTRUIR TABLA
    # ─────────────────────────────────────────
    table = []
    gap_sums = {method: 0 for method in all_results}
    gap_counts = {method: 0 for method in all_results}

    for i, inst in enumerate(instances, 1):

        row = [i, inst]
        LB = lb_list[i - 1]

        for method in all_results:

            if inst in all_results[method]:
                Z, tc = all_results[method][inst]
                gap = (Z - LB) / LB

                gap_sums[method] += gap
                gap_counts[method] += 1

                row.append(f"{gap:.4f}, {tc:.0f}")

            else:
                # instancia no disponible en ese método
                row.append("—")

        table.append(row)

    # ─────────────────────────────────────────
    # PROMEDIOS
    # ─────────────────────────────────────────
    avg_row = ["-", "AVG"]

    for method in all_results:
        if gap_counts[method] > 0:
            avg_gap = gap_sums[method] / gap_counts[method]
            avg_row.append(f"{avg_gap:.4f}")
        else:
            avg_row.append("—")

    table.append(avg_row)

    # ─────────────────────────────────────────
    # EXPORTAR
    # ─────────────────────────────────────────
    columns = ["i", "instancia"] + list(all_results.keys())
    df = pd.DataFrame(table, columns=columns)

    output_file = "code\resultados\comparacion_algoritmos.xlsx"
    df.to_excel(output_file, index=False)

    print("\n✅ Tabla generada correctamente:\n")
    print(df)
    print(f"\n📁 Guardado en: {output_file}")


if __name__ == "__main__":
    main()