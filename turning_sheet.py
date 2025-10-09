#!/usr/bin/env python3
# turning_sheet.py — matches your sheet, per-operation formulas, t_mc from V_f only

import math, csv

# Material presets: density [lb/in^3], default p_s [hp·min/in^3]
PRESETS = {
    "carbon steel": {"density": 0.283, "ps": 1.20},
    "alloy steel": {"density": 0.310, "ps": 1.35},
    "stainless steel (304)": {"density": 0.283, "ps": 1.80},
    "tool steel": {"density": 0.283, "ps": 1.90},
    "cast iron": {"density": 0.260, "ps": 0.95},
    "aluminum alloys (6061)": {"density": 0.100, "ps": 0.35},
    "brass": {"density": 0.310, "ps": 0.55},
    "nickel alloys": {"density": 0.300, "ps": 2.20},
    "magnesium alloys": {"density": 0.066, "ps": 0.25},
    "zinc alloys": {"density": 0.230, "ps": 0.50},
    "titanium alloys": {"density": 0.163, "ps": 2.40},
}

# Tool code shown in sheet: H/C/D
TOOLING_CHOICES = [("H", "HSS"), ("C", "Carbide"), ("D", "Ceramic/CBN/PCD")]

# Operation choices per pass
OPS = [
    "turn/thread",
    "bore/drill/tap/ream",
    "face/thread",
    "milling",
    "cutoff",
    "other",
]

HEADERS = [
    "Tool Type (HCD)",
    "Setup Time Per batch (hr)",
    "Load and Unload Time (s)",
    "Tool Positioning Time (s)",
    "Dimension (in.) lw",
    "Dimension (in.) da",
    "Dimension (in.) db",
    "Volume (in.^3) vm",
    "Specific Cutting Energy (hp min/in.^3) ps",
    "Available Power (hp) Pm",
    "Machining Time Max Power (s) tmp",
    "Rate of Surface Generation (in.^2/min) vf",
    "Milling Feed Speed (in./min) vt",  # kept for sheet compatibility; left blank
    "Area (in.^2) Am",
    "Machining Time Recommended conditions (s) tmc",
    "Time Corrected for Tool Wear (s) tm",
    "Time Corrected for Extra Tool Travel (s) t'm",
    "Pass",
    "Operation",
    "Material",
    "Notes",
]

def get_float(prompt, positive=True, default=None):
    while True:
        s = input(f"{prompt}" + (f" [default {default}]" if default is not None else "") + ": ").strip()
        if s == "" and default is not None:
            return float(default)
        try:
            x = float(s)
            if (not positive) or x > 0:
                return x
            print("  -> Enter a positive number.")
        except ValueError:
            print("  -> Not a number. Try again.")

def get_n(prompt, default=None):
    while True:
        n = get_float(prompt, positive=True, default=default)
        if 0.0 < n < 1.0:
            return n
        print("  -> n must be between 0 and 1 (e.g., 0.1–0.4). Try again.")

def pick_from_list(title, options):
    print(f"\n{title}:")
    for i, m in enumerate(options, 1):
        if isinstance(m, tuple):
            print(f"  {i}. {m[0]} - {m[1]}")
        else:
            print(f"  {i}. {m}")
    while True:
        sel = input("Select [number]: ").strip()
        if sel.isdigit() and 1 <= int(sel) <= len(options):
            return options[int(sel)-1]

def clamp_db_rough(db_r, db_final, da_start):
    if db_r < db_final:
        print(f"  -> Rough db smaller than final db; clamped to {db_final:.4f} in.")
        return db_final
    if db_r > da_start:
        print(f"  -> Rough db larger than start da; clamped to {da_start:.4f} in.")
        return da_start
    return db_r

def op_area_volume(operation, lw, da_in, db_used):
    """Return (Am, Vm) using per-operation formulas."""
    if operation == "turn/thread":
        Am = math.pi * lw * db_used
        Vm = (math.pi / 4.0) * lw * (da_in**2 - db_used**2)
    elif operation == "bore/drill/tap/ream":
        Am = math.pi * lw * da_in
        Vm = (math.pi / 4.0) * lw * (db_used**2 - da_in**2)
    elif operation == "face/thread":
        Am = (math.pi / 2.0) * da_in * (da_in - db_used)
        Vm = (math.pi / 2.0) * lw * da_in * (da_in - db_used)
    elif operation == "milling":
        # da_in = width (w), db_used = depth (ap)
        Am = lw * da_in
        Vm = lw * da_in * db_used
    else:  # cutoff/other → fallback turning style
        Am = math.pi * lw * max(db_used, 1e-9)
        Vm = (math.pi / 4.0) * lw * max(da_in**2 - db_used**2, 0.0)
    return Am, Vm

def compute_times(operation, Am, Vm, ps, Pm, n_tool, vf):
    """Return (tmc_s, tmp_s, tm_s, tm_prime_s). t_mc uses ONLY V_f."""
    tmp_s = 60.0 * ps * Vm / Pm if Pm > 0 else float("nan")
    tmc_s = 60.0 * (Am / vf)

    if not math.isnan(tmp_s) and tmp_s <= tmc_s:
        tm_s = tmc_s / (1.0 - n_tool)
    else:
        ratio = tmc_s / tmp_s if (tmp_s and tmp_s > 0) else float("inf")
        tm_s = tmp_s * (1.0 + (n_tool / (1.0 - n_tool)) * (ratio ** (1.0 / n_tool)))

    tm_prime_s = tm_s + 5.4 if operation in ["turn/thread", "face/thread", "bore/drill/tap/ream", "cutoff"] else tm_s
    return tmc_s, tmp_s, tm_s, tm_prime_s

def make_row(tool_code, setup_hr, load_s, toolpos_s,
             lw_in, da_in, db_used_in, vm_in3, ps, Pm, tmp_s,
             vf_in2min, Am_in2, tmc_s, tm_s, tm_prime_s,
             pass_name, operation, material, notes=""):
    return {
        "Tool Type (HCD)": tool_code,
        "Setup Time Per batch (hr)": setup_hr,
        "Load and Unload Time (s)": load_s,
        "Tool Positioning Time (s)": toolpos_s,
        "Dimension (in.) lw": lw_in,
        "Dimension (in.) da": da_in,
        "Dimension (in.) db": db_used_in,
        "Volume (in.^3) vm": vm_in3,
        "Specific Cutting Energy (hp min/in.^3) ps": ps,
        "Available Power (hp) Pm": Pm,
        "Machining Time Max Power (s) tmp": tmp_s,
        "Rate of Surface Generation (in.^2/min) vf": vf_in2min,
        "Milling Feed Speed (in./min) vt": "",  # always blank now
        "Area (in.^2) Am": Am_in2,
        "Machining Time Recommended conditions (s) tmc": tmc_s,
        "Time Corrected for Tool Wear (s) tm": tm_s,
        "Time Corrected for Extra Tool Travel (s) t'm": tm_prime_s,
        "Pass": pass_name,
        "Operation": operation,
        "Material": material,
        "Notes": notes,
    }

def main():
    print("=== Turning/Milling Worksheet Populator (t_mc from V_f) ===")

    # Geometry (full vs working)
    l_full = get_float("Full workpiece length (in)")
    lw     = get_float("Working length lw (in)")
    da0    = get_float("Starting diameter da (in)  [for milling: width w]")
    dbf    = get_float("Overall final diameter db (in)  [for milling: depth ap]")

    # Material
    mats = list(PRESETS.keys()) + ["custom"]
    mat_choice = pick_from_list("Workpiece material", mats)
    if mat_choice != "custom":
        density = PRESETS[mat_choice]["density"]
        ps_default = PRESETS[mat_choice]["ps"]
    else:
        density = get_float("Density (lb/in^3)", default=0.283)
        ps_default = get_float("Typical p_s (hp·min/in^3)", default=1.0)

    # Tool type code (H/C/D)
    code, _name = pick_from_list("Tool Type (H/C/D)", TOOLING_CHOICES)

    # Weight from FULL length (cyl stock)
    Vstock_in3 = (math.pi / 4.0) * (da0 ** 2) * l_full
    Mstock_lb  = density * Vstock_in3
    print(f"\nEstimated stock weight: {Mstock_lb:.2f} lb  (volume {Vstock_in3:.2f} in^3)")

    Pm = get_float("Available power P_m (hp)", default=5.0)
    n_tool = get_n("Tooling constant n (0<n<1)", default=0.2)

    setup_hr  = get_float("Setup time per batch (hr)", default=0.25)
    load_s    = get_float("Load & unload time (s)", default=45)
    toolpos_s = get_float("Tool positioning time (s)", default=10)

    rows = []
    rough = False
    finish = False
    db_rough = None
    ps_shared = ps_default
    tprime_r = 0.0
    tprime_f = 0.0

    # ---- Rough pass ----
    if input("Include ROUGH pass? [Y/n]: ").strip().lower() != "n":
        rough = True
        op_r = pick_from_list("Rough operation", OPS)
        # dimensions per op
        if op_r == "milling":
            da_r = get_float("Rough: milling WIDTH w (in)  [stored as da]")
            db_r = get_float("Rough: milling DEPTH ap (in) [stored as db]")
        else:
            db_r = get_float("Rough final diameter db_rough (in) [>= finish db]", default=dbf)
            db_r = clamp_db_rough(db_r, dbf, da0)
            da_r = da0

        ps_shared = get_float("Rough: specific cutting energy p_s (hp·min/in^3)", default=ps_default)
        vf_r = get_float("Rough: rate of surface generation V_f (in^2/min)")

        Am_r, Vm_r = op_area_volume(op_r, lw, da_r, db_r)
        tmc_r, tmp_r, tm_r, tmr_prime = compute_times(op_r, Am_r, Vm_r, ps_shared, Pm, n_tool, vf_r)
        tprime_r = tmr_prime
        if op_r != "milling":
            db_rough = db_r  # for finish-start diameter

        rows.append(make_row(code[0], setup_hr, load_s, toolpos_s,
                             lw, da_r, db_r, Vm_r, ps_shared, Pm, tmp_r,
                             vf_r, Am_r, tmc_r, tm_r, tmr_prime,
                             "Rough", op_r, mat_choice, notes=f"Weight={Mstock_lb:.2f} lb"))

    # ---- Finish pass ----
    if input("Include FINISH pass? [Y/n]: ").strip().lower() != "n":
        finish = True
        op_f = pick_from_list("Finish operation", OPS)

        if op_f == "milling":
            da_f = get_float("Finish: milling WIDTH w (in)  [stored as da]")
            db_f = get_float("Finish: milling DEPTH ap (in) [stored as db]")
        else:
            da_f = db_rough if (rough and db_rough is not None) else da0
            db_f = dbf

        vf_f = get_float("Finish: rate of surface generation V_f (in^2/min)")

        Am_f, Vm_f = op_area_volume(op_f, lw, da_f, db_f)
        tmc_f, tmp_f, tm_f, tmf_prime = compute_times(op_f, Am_f, Vm_f, ps_shared, Pm, n_tool, vf_f)
        tprime_f = tmf_prime

        rows.append(make_row(code[0], setup_hr, load_s, toolpos_s,
                             lw, da_f, db_f, Vm_f, ps_shared, Pm, tmp_f,
                             vf_f, Am_f, tmc_f, tm_f, tmf_prime,
                             "Finish", op_f, mat_choice, notes=f"Weight={Mstock_lb:.2f} lb (p_s & P_m reused)"))

    if not rows:
        print("No passes selected. Exiting.")
        return

    # ===== Costs =====
    print("\n=== Cost Inputs ===")
    cost_per_lb = get_float("Material cost per unit weight ($/lb)")
    hourly_rate = get_float("Operator hourly rate ($/hr)")
    num_parts   = get_float("Number of parts in batch", positive=True, default=1)

    material_cost_per_part = cost_per_lb * Mstock_lb
    setup_cost_per_part = (hourly_rate * setup_hr) / num_parts
    nonprod_seconds = load_s + (toolpos_s if rough else 0) + (toolpos_s if finish else 0)
    nonprod_cost_per_part = hourly_rate * (nonprod_seconds / 3600.0)
    total_machining_seconds = (tprime_r if rough else 0.0) + (tprime_f if finish else 0.0)
    machining_cost_per_part = hourly_rate * (total_machining_seconds / 3600.0)
    total_cost_per_part = material_cost_per_part + setup_cost_per_part + nonprod_cost_per_part + machining_cost_per_part

    # ===== Write CSV =====
    out = "turning_sheet.csv"
    need_header = False
    try:
        with open(out, "r"):
            pass
    except FileNotFoundError:
        need_header = True

    with open(out, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADERS)
        if need_header:
            w.writeheader()
        for r in rows:
            w.writerow(r)

    # ===== Print cost summary =====
    print("\n=== Cost Summary (per part) ===")
    print(f"Material cost:         ${material_cost_per_part:,.2f}  (weight {Mstock_lb:.2f} lb @ ${cost_per_lb:.2f}/lb)")
    print(f"Setup cost per part:   ${setup_cost_per_part:,.2f}  (setup {setup_hr:.3f} hr @ ${hourly_rate:.2f}/hr ÷ {int(num_parts)} parts)")
    print(f"Non-productive cost:   ${nonprod_cost_per_part:,.2f}  ({nonprod_seconds:.1f} s @ ${hourly_rate:.2f}/hr)")
    print(f"Machining cost:        ${machining_cost_per_part:,.2f}  ({total_machining_seconds:.1f} s @ ${hourly_rate:.2f}/hr)")
    print(f"--------------------------------------------------------------")
    print(f"TOTAL cost per part:   ${total_cost_per_part:,.2f}")
    print(f'\nRows saved to "turning_sheet.csv".')

if __name__ == "__main__":
    main()
