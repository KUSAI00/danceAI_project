import sys 
import json 
import math

# -----------------------------
# CONFIGURAZIONE
# -----------------------------
GRID_W = 25
GRID_H = 25
TIME_STEP = 1.0       # 1 secondo per slot
MAX_SPEED = 4         # distanza massima per slot
MAX_PAUSE = 60        # durata massima della pausa (in slot/secondi)

# ----------------------------- 
# UTILITIES 
# ----------------------------- 
def t_to_slot(t: float):
    return int(math.floor(t / TIME_STEP))

def interpolate(frm, to, steps):
    """Linear interpolation tra due celle"""
    path = []
    x0, y0 = frm
    x1, y1 = to
    for i in range(steps):
        a = i / max(1, steps-1)
        xr = round(x0 + (x1 - x0) * a)
        yr = round(y0 + (y1 - y0) * a)
        path.append([xr, yr])
    return path

def get_active_interval(events, dancer):
    enter_times = [e["start"] for e in events if e["dancer"]==dancer and e["action"]=="enter"]
    exit_times  = [e["end"]   for e in events if e["dancer"]==dancer and e["action"]=="exit"]

    start_time = min(enter_times) if enter_times else None
    end_time   = max(exit_times)  if exit_times else None  # None = fino alla fine
    return start_time, end_time

# -----------------------------
# VALIDATORE 
# -----------------------------
def validate(parsed):
    dancers = parsed["dancers"]
    duration = parsed["duration"]
    events = parsed["events"]

    total_slots = t_to_slot(duration) + 1
    occupancy = {d: [None]*total_slots for d in dancers}
    timeline = [{} for _ in range(total_slots)]
    violations = []

    # --- Controllo ballerini che non entrano mai
    for d in dancers:
        enters = [e for e in events if e["dancer"]==d and e["action"]=="enter"]
        has_position = any(e.get("from") is not None or e.get("to") is not None for e in events if e["dancer"]==d)
    
        if not enters and not has_position:
        # nessun enter e nessuna posizione → violazione
            violation = {
                "type": "missing_enter",
                "dancer": d
            }
            violations.append(violation)
        elif not enters and has_position:
            # nessun enter ma c'è posizione → consideriamo l'entrata implicita
            violation = {
                "type": "implicit_enter",
                "dancer": d
            }
            violations.append(violation)

# --- Controllo ballerini che non escono mai
    for d in dancers:
        exits = [e for e in events if e["dancer"]==d and e["action"]=="exit"]
        last_pos_events = [e for e in events if e["dancer"]==d and (e.get("from") is not None or e.get("to") is not None)]

    if not exits:
        if last_pos_events:
            # Consideriamo l'uscita implicita alla fine della timeline
            report_info = {
                "type": "implicit_exit",
                "dancer": d
            }
            violations.append(report_info)
        else:
            # Nessuna posizione, nessun exit → segnalazione critica
            violation = {
                "type": "missing_exit",
                "dancer": d
            }
            violations.append(violation)


    # --- Riempio occupancy con interpolazioni
    for e in events:
        d = e["dancer"]
        start = t_to_slot(e["start"])
        end = t_to_slot(e["end"])
        frm = e.get("from")
        to  = e.get("to")
        if frm is None or to is None:
            continue
        steps = max(1, end-start)
        path = interpolate([frm["x"], frm["y"]], [to["x"], to["y"]], steps)
        for i, slot in enumerate(range(start, start+len(path))):
            if slot < total_slots:
                occupancy[d][slot] = path[i]

    # --- Completo None con ultima posizione nota
    for d in dancers:
        last = None
        start_time, end_time = get_active_interval(events, d)
        for t in range(total_slots):
            if start_time is not None and t < start_time:
                occupancy[d][t] = None  # prima dell'entrata non considerato
                continue
            if end_time is not None and t >= end_time:
                occupancy[d][t] = None  # dopo l'exit non considerato
                continue

            if occupancy[d][t] is None and last is not None:
                occupancy[d][t] = last
            elif occupancy[d][t] is not None:
                last = occupancy[d][t]

            if occupancy[d][t] is not None:
                timeline[t][d] = occupancy[d][t]

    # --- Collisioni e out-of-bounds
    for t in range(total_slots):
        seen = {}
        for d in dancers:
            start_time, end_time = get_active_interval(events, d)
            if start_time is None or t < start_time or (end_time is not None and t >= end_time):
                continue  # ballerino non attivo
            pos = occupancy[d][t]
            if pos is None:
                continue
            x, y = pos
            if not (0 <= x < GRID_W) or not (0 <= y < GRID_H):
                violations.append({
                    "type": "out_of_bounds",
                    "dancer": d,
                    "time": t,
                    "position": pos
                })
            key = tuple(pos)
            seen.setdefault(key, []).append(d)
        for pos_key, ds in seen.items():
            if len(ds) > 1:
                violations.append({
                    "type":"collision",
                    "time": t,
                    "position": pos_key,
                    "dancers": ds
                })

    # --- Velocità massima
    for d in dancers:
        start_time, end_time = get_active_interval(events, d)
        if start_time is None:
            continue
        for t in range(total_slots-1):
            if t < start_time or (end_time is not None and t+1 >= end_time):
                continue
            p0 = occupancy[d][t]
            p1 = occupancy[d][t+1]
            if p0 is not None and p1 is not None:
                cheb = max(abs(p0[0]-p1[0]), abs(p0[1]-p1[1]))
                if cheb > MAX_SPEED:
                    violations.append({
                        "type":"speed_violation",
                        "dancer": d,
                        "time": t,
                        "distance": cheb
                    })

    # --- Pause eccessive 
    for d in dancers:
        start_time, end_time = get_active_interval(events, d)
        if start_time is None:
            continue  # non consideriamo ballerini che non entrano

        pause_start = None
        last_pos = None

        for t, frame in enumerate(timeline):
            if t < start_time or (end_time is not None and t >= end_time):
                last_pos = None
                pause_start = None
                continue

            pos = frame.get(d)
            if pos is None:
                last_pos = None
                pause_start = None
                continue

            if last_pos is None:
                last_pos = pos
                pause_start = t
                continue

            if pos == last_pos:
                continue
            else:
                pause_end = t
                duration = pause_end - pause_start
                if duration >= MAX_PAUSE:
                    violations.append({
                        "type": "excessive_pause",
                        "dancer": d,
                        "start": pause_start,
                        "end": pause_end,
                        "duration": duration
                    })
                last_pos = pos
                pause_start = t

        # fine timeline
        if pause_start is not None and last_pos is not None:
            pause_end = len(timeline)
            duration = pause_end - pause_start
            if duration >= MAX_PAUSE:
                violations.append({
                    "type": "excessive_pause",
                    "dancer": d,
                    "start": pause_start,
                    "end": pause_end,
                    "duration": duration
                })

    report = {
        "valid": len(violations) == 0,
        "violations": violations
        #"occupancy": occupancy,
        #"total_slots": total_slots
    }
    return report

# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":
    file_path = sys.argv[1]
    with open(file_path, "r") as f:
        parsed = json.load(f)

    report = validate(parsed)

    print("\n--- Dettagli violazioni ---")
    for v in report["violations"]:
        if v["type"] == "missing_enter":
            print(f"[CRITICAL] Dancer '{v['dancer']}' has no explicit enter and no initial position")
        elif v["type"] == "implicit_enter":
            print(f"[INFO] Dancer '{v['dancer']}' has no explicit enter; using initial position as implicit entry.")
        elif v["type"] == "missing_exit":
            print(f"[CRITICAL] Dancer '{v['dancer']}' has no explicit exit and no final position")
        elif v["type"] == "implicit_exit":
            print(f"[INFO] Dancer '{v['dancer']}' has no explicit exit; using final position as implicit exit.")
        elif v["type"] == "excessive_pause":
            print(f"[MEDIUM] Excessive pause for '{v['dancer']}': stationary for {v['duration']} consecutive slots "
            f"(start={v['start']}, end={v['end']})")
        elif v["type"] == "collision":
            dancers_str = ", ".join(v['dancers'])
            print(f"[HIGH] Collision at position {v['position']} between dancers {dancers_str} at time {v['time']}")
        elif v["type"] == "speed_violation":
            print(f"[HIGH] Excessive speed for '{v['dancer']}' at time {v['time']}: distance {v['distance']}")
        elif v["type"] == "out_of_bounds":
            print(f"[HIGH] Out of bounds for '{v['dancer']}' at time {v['time']}: position {v['position']}")
        else:
            print(f"[INFO] Unclassified violation: {v}")

    print("\n--- Report JSON ---")
    print(json.dumps(report, indent=2))

    if report["valid"]:
        print("\nValid choreography!")
    else:
        print("\nTotal violations found:", len(report["violations"]))
