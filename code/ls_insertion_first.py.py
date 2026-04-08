import os
import math
import time
import pandas as pd

# ─────────────────────────────────────────────
# PARÁMETROS
# ─────────────────────────────────────────────
INSTANCES_DIR = "NWJSSP Instances"
OUTPUT_FILE   = "resultados\\NWJSSP_OADG_LS_INSERTION_FIRST.xlsx"   # ← archivo separado

TIME_LIMIT_PER_BLOCK = 0.01
TIME_LIMIT_LS = 3600.0   # 1 hora por instancia (requisito del trabajo)

INSTANCES = [
    "ft06.txt",           "ft06r.txt",
    "ft10.txt",           "ft10r.txt",
    "ft20.txt",           "ft20r.txt",
    "tai_j10_m10_1.txt",    "tai_j10_m10_1r.txt",
    "tai_j100_m10_1.txt",   "tai_j100_m10_1r.txt",
    "tai_j100_m100_1.txt",  "tai_j100_m100_1r.txt",
    "tai_j1000_m10_1.txt",  "tai_j1000_m10_1r.txt",
    "tai_j1000_m100_1.txt", "tai_j1000_m100_1r.txt"
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
        self.intervals: list[tuple[int, int]] = []

    def add(self, b: int, e: int) -> None:
        self.intervals.append((b, e))

    def max_end_before(self, threshold: int) -> int:
        max_e = 0
        for b, e in self.intervals:
            if b < threshold:
                max_e = max(max_e, e)
        return max_e

# ─────────────────────────────────────────────
# LECTURA DE INSTANCIAS
# ─────────────────────────────────────────────
def read_instance(file):
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
    return [[0] * len(job.operations) if len(job.operations) <= 1 else 
            [0] + [sum(op.p for op in job.operations[:u+1]) for u in range(len(job.operations)-1)]
            for job in jobs]

# ─────────────────────────────────────────────
# OFFSETS NO-WAIT
# ─────────────────────────────────────────────
def compute_offsets(job):
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
    machine_available = [0] * m
    total_flow = 0
    for idx in range(pos):
        total_flow += schedule_job(jobs[sequence[idx]], machine_available, sequence[idx], None)
    total_flow += schedule_job(jobs[j], machine_available, j, None)
    for idx in range(pos, len(sequence)):
        total_flow += schedule_job(jobs[sequence[idx]], machine_available, sequence[idx], None)
    return total_flow

# ─────────────────────────────────────────────
# FUNCIONES PARA PROGRAMACIÓN PRECISA FINAL
# ─────────────────────────────────────────────
def find_start_preciso(job, machines, offsets):
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
    machines = [Machine(i) for i in range(m)]
    total_flow = 0
    schedule = [] if save_schedule else None
    for j in sequence:
        total_flow += schedule_job_preciso(jobs[j], machines, j, schedule, offsets_list[j])
    return (total_flow, schedule) if save_schedule else total_flow

# ─────────────────────────────────────────────
# MEJOR POSICIÓN CON BÚSQUEDA POR BLOQUES TEMPORIZADOS (NEH)
# ─────────────────────────────────────────────
def find_best_insertion(sequence, j, jobs, m, block_size, time_limit):
    n_pos = len(sequence) + 1
    best_pos = 0
    best_value = float("inf")
    pos = 0
    while pos < n_pos:
        end_block = min(pos + block_size, n_pos)
        t_bloque = time.time()
        for p in range(pos, end_block):
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
    n = len(jobs)
    block_size = max(10, int(math.sqrt(n)))
    order = sorted(
        range(n),
        key=lambda j: jobs[j].release + sum(op.p for op in jobs[j].operations),
        reverse=True
    )
    sequence = []
    for j in order:
        best_pos, _ = find_best_insertion(sequence, j, jobs, m, block_size, TIME_LIMIT_PER_BLOCK)
        sequence.insert(best_pos, j)
    return sequence

# ─────────────────────────────────────────────
# EXPORTAR RESULTADOS A EXCEL (mismo formato que NEH)
# ─────────────────────────────────────────────
def write_results_to_excel(results, output_file):
    os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".", exist_ok=True)
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
# CARGA (O CREA) SOLUCIÓN INICIAL
# ─────────────────────────────────────────────
def load_or_create_initial(jobs, m, sheet_name):
    path = f"initial solutions/{sheet_name}.txt"
    if os.path.exists(path):
        with open(path) as f:
            return list(map(int, f.read().split()))
    else:
        sequence = construct_solution(jobs, m)
        os.makedirs("initial solutions", exist_ok=True)
        with open(path, "w") as f:
            f.write(" ".join(map(str, sequence)))
        print(f"[NEH creado y guardado] {sheet_name}")
        return sequence

# ─────────────────────────────────────────────
# EVALUAR MOVE DE INSERCIÓN
# ─────────────────────────────────────────────
def evaluate_insertion_move(seq, i, pos, jobs, m):
    job = seq[i]
    temp = seq[:i] + seq[i+1:]
    return evaluate_insertion(temp, job, pos, jobs, m)

# ─────────────────────────────────────────────
# LOCAL SEARCH INSERTION + FIRST IMPROVEMENT (con límite 1 hora)
# ─────────────────────────────────────────────
def local_search_insertion_first(seq, jobs, m):
    n = len(seq)
    t_start = time.time()

    while True:
        if time.time() - t_start > TIME_LIMIT_LS:
            print("   → Tiempo límite de 1 hora alcanzado")
            break

        improved = False
        current_val = evaluate_sequence(seq, jobs, m)

        for i in range(n):
            for pos in range(n):
                if pos == i:
                    continue
                val = evaluate_insertion_move(seq, i, pos, jobs, m)
                if val < current_val:
                    job = seq.pop(i)
                    seq.insert(pos if pos < i else pos, job)
                    improved = True
                    current_val = val
                    break
            if improved:
                break

        if not improved:
            break
    return seq

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    results = {}
    for inst in INSTANCES:
        filepath = os.path.join(INSTANCES_DIR, inst)
        if not os.path.exists(filepath):
            print(f"[SKIP] {inst} — archivo no encontrado")
            continue

        jobs, m = read_instance(filepath)
        sheet_name = inst.replace(".txt", "")

        seq = load_or_create_initial(jobs, m, sheet_name)

        t0 = time.time()
        seq = local_search_insertion_first(seq, jobs, m)
        compute_time_ms = round((time.time() - t0) * 1000)

        offsets_list = precompute_offsets(jobs)
        total_flow, schedule = evaluate_sequence_preciso(seq, jobs, m, offsets_list, save_schedule=True)

        job_start_times = [None] * len(jobs)
        for op in schedule:
            if op["operation"] == 0:
                job_start_times[op["job"]] = op["start"]

        results[sheet_name] = (total_flow, compute_time_ms, job_start_times)
        print(f"[OK] {inst:<30} Z={total_flow:>10}  tiempo={compute_time_ms:>6} ms")

    if results:
        write_results_to_excel(results, OUTPUT_FILE)
    else:
        print("No se procesó ninguna instancia.")

if __name__ == "__main__":
    main()