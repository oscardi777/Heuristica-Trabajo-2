import os
import math
import time
import pandas as pd


# ─────────────────────────────────────────────
# PARÁMETROS
# ─────────────────────────────────────────────
INSTANCES_DIR = "NWJSSP Instances"
OUTPUT_FILE   = "resultados\\NWJSSP_OADG_NEH(BestImprovement_LocalSearch).xlsx"

TIME_LIMIT_PER_BLOCK = 0.01 # Tiempo máximo en segundos por bloque de posiciones
TIME_LIMIT_LS = 3600  # 1 hora en segundos

INSTANCES = [
    #"ft06.txt",           "ft06r.txt",
    #"ft10.txt",           "ft10r.txt",
    #"ft20.txt",           "ft20r.txt",
    "tai_j10_m10_1.txt",    "tai_j10_m10_1r.txt",
    "tai_j100_m10_1.txt",   "tai_j100_m10_1r.txt",
    "tai_j100_m100_1.txt",  "tai_j100_m100_1r.txt",
    #"tai_j1000_m10_1.txt",  "tai_j1000_m10_1r.txt",
    #"tai_j1000_m100_1.txt", "tai_j1000_m100_1r.txt"
]


# ─────────────────────────────────────────────
# ESTRUCTURAS DE DATOS
# ─────────────────────────────────────────────
class Operation:
    def __init__(self, machine, processing_time):
        self.machine = machine
        self.p = processing_time

class Job:
    def __init__(self, operations, release):
        self.operations = operations
        self.release = release

# ─────────────────────────────────────────────
# ESTRUCTURA MACHINE SIMPLIFICADA
# ─────────────────────────────────────────────
class Machine:
    def __init__(self, id: int):
        self.id = id
        self.intervals: list[tuple[int, int]] = []   # (begin, end)

    def add(self, b: int, e: int):
        """Añade un intervalo (no necesita orden)."""
        self.intervals.append((b, e))

    def max_end_before(self, threshold: int):
        """Devuelve el mayor 'end' de cualquier operación cuyo 'begin' < threshold."""
        max_e = 0
        for b, e in self.intervals:
            if b < threshold:
                max_e = max(max_e, e)
        return max_e

# ─────────────────────────────────────────────
# LECTURA DE INSTANCIAS
# ─────────────────────────────────────────────
def read_instance(file):
    """
    Lee una instancia NWJSSP desde archivo de texto, para extraer los datos de la instancia.
    Asumiendo formato del Anexo 2
    """
    with open(file) as f:
        n, m = map(int, f.readline().split())
        jobs = []
        for _ in range(n):
            data = list(map(int, f.readline().split()))
            operations = [
                Operation(data[2*i], data[2*i + 1])
                for i in range(m)
            ]
            jobs.append(Job(operations, release=data[-1]))

    return jobs, m

# ─────────────────────────────────────────────
# OFFSETS PRECOMPUTADOS
# ─────────────────────────────────────────────
def precompute_offsets(jobs):
    """
    Precomputa offsets para todos los jobs (usado solo en programación precisa final).
    """
    return [[0] * len(job.operations) if len(job.operations) <= 1 else 
            [0] + [sum(op.p for op in job.operations[:u+1]) for u in range(len(job.operations)-1)]
            for job in jobs]

# ─────────────────────────────────────────────
# OFFSETS NO-WAIT
# ─────────────────────────────────────────────
def compute_offsets(job):
    """
    Calcula el desplazamiento acumulado de cada operación respecto al
    inicio del trabajo. offset[u] = sum de tiempos de op. 0..u-1.
    Bajo No-Wait, la operación u comienza exactamente en start + offset[u].
    """
    offsets = [0] * len(job.operations)
    total = 0
    for u, op in enumerate(job.operations[:-1]):
        total += op.p
        offsets[u + 1] = total

    return offsets


# ─────────────────────────────────────────────
# INICIO FACTIBLE MÍNIMO BAJO NO-WAIT
# ─────────────────────────────────────────────
def find_start(job, machine_available, offsets):
    """
    Calcula el inicio factible mínimo bajo la restricción No-Wait:
    start = max(r_j, max_u{ machine_available[machine_u] - offset[u] })
    """
    start = job.release
    for u, op in enumerate(job.operations):
        required = machine_available[op.machine] - offsets[u]
        if required > start:
            start = required

    return start

# ─────────────────────────────────────────────
# PROGRAMAR UN TRABAJO
# ─────────────────────────────────────────────
def schedule_job(job, machine_available, job_id, schedule):
    """
    Inserta job_id en la programación actual.
    Actualiza machine_available y, si schedule no es None, registra ops.
    Retorna el tiempo de finalización del trabajo (Cj).
    """
    offsets = compute_offsets(job)
    start   = find_start(job, machine_available, offsets)
    completion = 0
    for u, op in enumerate(job.operations):
        begin  = start + offsets[u]
        finish = begin + op.p
        machine_available[op.machine] = finish
        if schedule is not None:
            schedule.append({
                "job": job_id, "machine": op.machine,
                "operation": u, "start": begin, "finish": finish
            })
        completion = finish

    return completion

# ─────────────────────────────────────────────
# EVALUAR SECUENCIA COMPLETA
# ─────────────────────────────────────────────
def evaluate_sequence(sequence, jobs, m, save_schedule=False):
    """
    Evalúa una secuencia completa y calcula el Total Flow Time (suma Cj).
    Si save_schedule=True devuelve también el schedule completo.
    """
    machine_available = [0] * m
    total_flow = 0
    schedule   = [] if save_schedule else None
    for j in sequence:
        Cj = schedule_job(jobs[j], machine_available, j, schedule)
        total_flow += Cj

    return (total_flow, schedule) if save_schedule else total_flow

# ─────────────────────────────────────────────
# EVALUAR INSERCIÓN
# ─────────────────────────────────────────────
def evaluate_insertion(sequence, j, pos, jobs, m):
    """
    Evalúa el Total Flow Time de insertar j en la posición pos de
    sequence, recorriendo los tres segmentos sin construir lista temporal:
        sequence[0..pos-1]  →  j  →  sequence[pos..end]
    """
    machine_available = [0] * m
    total_flow = 0

    for idx in range(pos):
        total_flow += schedule_job(
            jobs[sequence[idx]], machine_available, sequence[idx], None
        )

    total_flow += schedule_job(jobs[j], machine_available, j, None)

    for idx in range(pos, len(sequence)):
        total_flow += schedule_job(
            jobs[sequence[idx]], machine_available, sequence[idx], None
        )

    return total_flow

# ─────────────────────────────────────────────
# FUNCIONES PARA PROGRAMACIÓN PRECISA FINAL
# ─────────────────────────────────────────────
def find_start_preciso(job, machines, offsets):
    """
    Calcula el inicio factible mínimo preciso bajo No-Wait usando Machine
    (detecta huecos y permite inserciones más ajustadas).
    """
    start = job.release
    while True:
        max_candidate = start
        feasible = True
        for u, op in enumerate(job.operations):
            b_op = start + offsets[u]
            e_op = b_op + op.p
            max_ek = machines[op.machine].max_end_before(e_op)
            if max_ek > b_op:
                feasible = False
                candidate = max_ek - offsets[u]
                max_candidate = max(max_candidate, candidate)
        if feasible:
            return start
        start = max_candidate

def schedule_job_preciso(job, machines, job_id, schedule, offsets):
    """
    Programa un trabajo usando find_start_preciso y Machine (versión precisa).
    """
    start = find_start_preciso(job, machines, offsets)
    completion = 0
    for u, op in enumerate(job.operations):
        begin = start + offsets[u]
        finish = begin + op.p
        machines[op.machine].add(begin, finish)
        if schedule is not None:
            schedule.append({
                "job": job_id, "machine": machines[op.machine].id,
                "operation": u, "start": begin, "finish": finish
            })
        completion = finish
    return completion

def evaluate_sequence_preciso(sequence, jobs, m, offsets_list, save_schedule=False):
    """
    Evalúa la secuencia completa con programación precisa (huecos permitidos).
    Retorna Z real y schedule listo para Excel.
    """
    machines = [Machine(i) for i in range(m)]
    total_flow = 0
    schedule = [] if save_schedule else None
    for j in sequence:
        total_flow += schedule_job_preciso(jobs[j], machines, j, schedule, offsets_list[j])
    return (total_flow, schedule) if save_schedule else total_flow

# ─────────────────────────────────────────────
# MEJOR POSICIÓN CON BÚSQUEDA POR BLOQUES TEMPORIZADOS
# ─────────────────────────────────────────────
def find_best_insertion(sequence, j, jobs, m, block_size, time_limit):
    """
    Encuentra la mejor posición para insertar j en sequence usando
    búsqueda por bloques con límite de tiempo por bloque:
      - La secuencia se divide en bloques consecutivos de tamaño block_size.
      - Cada bloque tiene un time_limit segundos.
        Si se agota el tiempo dentro del bloque, se interrumpe ese bloque
        y se avanza al siguiente.
      - Al finalizar se retorna la mejor posición encontrada en cualquier bloque.
    """
    n_pos = len(sequence) + 1
    best_pos = 0
    best_value = float("inf")

    pos = 0
    while pos < n_pos:
        end_block = min(pos + block_size, n_pos)
        t_bloque = time.time()

        for p in range(pos, end_block):
            # Tiempo agotado en este bloque → saltar al siguiente
            if time.time() - t_bloque > time_limit:
                break
            value = evaluate_insertion(sequence, j, p, jobs, m)
            if value < best_value:
                best_value = value
                best_pos = p

        pos = end_block

    return best_pos, best_value


# ─────────────────────────────────────────────
# HEURÍSTICA CONSTRUCTIVA NEH
# ─────────────────────────────────────────────
def construct_solution(jobs, m):
    """
    Heurística NEH adaptada al NWJSSP con búsqueda por bloques temporizados:
    1. Ordena los trabajos de mayor a menor por r_j + sum(p_ju).
    2. Inserta cada trabajo en la mejor posición encontrada mediante
       búsqueda por bloques con límite de tiempo por bloque.
            block_size = max(10, sqrt(n)) — adaptativo al tamaño de la instancia.
    """
    n = len(jobs)
    block_size = max(10, int(math.sqrt(n)))

    order = sorted(
        range(n),
        key=lambda j: jobs[j].release + sum(op.p for op in jobs[j].operations),
        reverse=True
    )

    sequence = []
    for j in order:
        best_pos, _ = find_best_insertion(
            sequence, j, jobs, m, block_size, TIME_LIMIT_PER_BLOCK
        )
        sequence.insert(best_pos, j)

    return sequence

# ─────────────────────────────────────────────
# EXPORTAR RESULTADOS A EXCEL
# ─────────────────────────────────────────────
def write_results_to_excel(results, output_file):
    """
    Exporta los resultados de todas las instancias a un archivo Excel.
    Siguiendo el formato especificado en el Anexo 3
    """
    os.makedirs(
        os.path.dirname(output_file) if os.path.dirname(output_file) else ".",
        exist_ok=True
    )
    writer_kwargs = (
        dict(engine="openpyxl", mode="a", if_sheet_exists="replace")
        if os.path.exists(output_file)
        else dict(engine="openpyxl", mode="w")
    )
    with pd.ExcelWriter(output_file, **writer_kwargs) as writer:
        for sheet_name, (total_flow, compute_time_ms, job_start_times) in results.items():
            df = pd.DataFrame([
                [total_flow, compute_time_ms],
                job_start_times
            ])
            df.to_excel(writer, sheet_name=sheet_name, header=False, index=False)

    print(f"\nResultados guardados en: {output_file}")

# ─────────────────────────────────────────────
# BEST IMPROVEMENT
# ─────────────────────────────────────────────
def local_search_best_improvement(initial_sequence, jobs, m, offsets_list, time_limit_sec=3600):
    B = list(initial_sequence)           # B ← InitialSolution()
    best_z = evaluate_sequence_preciso(B, jobs, m, offsets_list)
    fin = False
    start_ls = time.time()

    while not fin and (time.time() - start_ls < time_limit_sec):
        fin = True
        best_neighbor = None
        best_neighbor_z = float('inf')
        h = 0

        while h < len(B) - 1:
            if time.time() - start_ls >= time_limit_sec:
                break

            P = B[:]                         # copia
            P[h], P[h + 1] = P[h + 1], P[h]  # intercambio consecutivo

            z = evaluate_sequence_preciso(P, jobs, m, offsets_list)

            if z < best_neighbor_z:
                best_neighbor_z = z
                best_neighbor = P[:]

            h += 1

        if best_neighbor is not None and best_neighbor_z < best_z:
            B = best_neighbor
            best_z = best_neighbor_z
            fin = False                      # continuar buscando

    return B, best_z


# ─────────────────────────────────────────────
# MAIN - EXACTAMENTE COMO PEDISTE
# ─────────────────────────────────────────────
def main():
    results = {}
    for inst in INSTANCES:
        filepath = os.path.join(INSTANCES_DIR, inst)
        if not os.path.exists(filepath):
            print(f"[SKIP] {inst} — archivo no encontrado")
            continue

        jobs, m = read_instance(filepath)
        n = len(jobs)
        sheet_name = inst.replace(".txt", "")
        initial_txt = f"initial solutions/{sheet_name}.txt"

        # 1. Revisar si existe solución inicial
        if os.path.exists(initial_txt):
            with open(initial_txt) as f:
                sequence = list(map(int, f.readline().split()))
            print(f"[LOAD] {inst:<30} initial solution cargada")
        else:
            # Calcular con NEH solo si no existe
            sequence = construct_solution(jobs, m)
            os.makedirs("initial solutions", exist_ok=True)
            with open(initial_txt, "w") as f:
                f.write(" ".join(map(str, sequence)))
            print(f"[NEH] {inst:<30} solución inicial calculada y guardada")

        offsets_list = precompute_offsets(jobs)

        # 2. Iniciar contador de tiempo y Local Search
        t0 = time.time()
        improved_sequence, total_flow = local_search_best_improvement(
            sequence, jobs, m, offsets_list, TIME_LIMIT_LS
        )
        compute_time_ms = round((time.time() - t0) * 1000)

        # 3. Preparar schedule para Excel
        _, schedule = evaluate_sequence_preciso(improved_sequence, jobs, m, offsets_list, save_schedule=True)
        job_start_times = [None] * n
        for op in schedule:
            if op["operation"] == 0:
                job_start_times[op["job"]] = op["start"]

        results[sheet_name] = (total_flow, compute_time_ms, job_start_times)

        print(f"[LS OK] {inst:<30} Z={total_flow:>10}  tiempo={compute_time_ms:>6} ms")

    if results:
        write_results_to_excel(results, OUTPUT_FILE)
        print(f"\nResultados guardados en: {OUTPUT_FILE}")
    else:
        print("No se procesó ninguna instancia.")


if __name__ == "__main__":
    main()