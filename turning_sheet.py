#!/usr/bin/env python3
# turning_sheet.py — matches your sheet, prints cost summary


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

TOOLING_CHOICES = [("H", "HSS"), ("C", "Carbide"), ("D", "Ceramic/CBN/PCD")]
OPERATIONS = ["turning", "facing", "cutoff", "boring", "other"]

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
        raw = input(f"{prompt}" + (f" [default {default}]" if default is not None else "") + ": ").strip()
        if raw == "" and default is not None:
            return float(default)
        try:
            val = float(raw)
            if (not positive) or val > 0:
                return val
            print("  -> Enter a positive number.")
        except ValueError:
            print("  -> Not a number. Try again.")

def pick_from_list(title, options):
    print(f"\n{title}:")
    for i, opt in enumerate(options, 1):
        label = f"{opt[0]} - {opt[1]}" if isinstance(opt, tuple) else str(opt)
        print(f"  {i}. {label}")
    while True:
        s = input("Select [number]: ").strip()
        if s.isdigit() and 1 <= int(s) <= len(options):
            return options[int(s)-1]

def get_n(prompt, default=None):
    while True:
        n = get_float(prompt, positive=True, default=default)
        if 0.0 < n < 1.0:
            return n
        print("  -> n must be between 0 and 1 (e.g., 0.1–0.4). Try again.")

def clamp_db_rough(db_r, db_final, da_start):
    if db_r < db_final:
        print(f"  -> Rough db smaller than final db; clamped to {db_final:.4f} in.")
        return db_final
    if db_r > da_start:
        print(f"  -> Rough db larger than start da; clamped to {da_start:.4f} in.")
        return da_start
    return db_r

def make_row(tool_code, setup_hr, load_s, toolpos_s,
             lw_in, da_in, db_used_in,
             vm_in3, ps, Pm, tmp_s, vf_in2min, Am_in2, tmc_s, tm_s, tm_prime_s,
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
        "Milling Feed Speed (in./min) vt": "",  # blank
        "Area (in.^2) Am": Am_in2,
        "Machining Time Recommended conditions (s) tmc": tmc_s,
        "Time Corrected for Tool Wear (s) tm": tm_s,
        "Time Corrected for Extra Tool Travel (s) t'm": tm_prime_s,
        "Pass": pass_name,
        "Operation": operation,
        "Material": material,
        "Notes": notes,
    }

def compute_pass_row(lw_in, da_in, db_used_in, ps, Pm, vf_in2min, n_tool, operation):
    # Volumes & areas (using working length)
    vm_in3 = (math.pi / 4.0) * (da_in**2 - db_used_in**2) * lw_in
    Am_in2 = math.pi * db_used_in * lw_in

    # Times
    tmc_s = 60.0 * (Am_in2 / vf_in2min)                   # from user-input V_f
    tmp_s = 60.0 * ps * vm_in3 / Pm if Pm > 0 else float("nan")

    # Final machining time with n-rule
    if not math.isnan(tmp_s) and tmp_s <= tmc_s:
        tm_s = tmc_s / (1.0 - n_tool)
    else:
        ratio = tmc_s / tmp_s if (tmp_s and tmp_s > 0) else float("inf")
        tm_s = tmp_s * (1.0 + (n_tool / (1.0 - n_tool)) * (ratio ** (1.0 / n_tool)))

    # Tool-travel correction
    tm_prime_s = tm_s + 5.4 if operation in ["turning", "facing", "cutoff", "boring"] else tm_s
    return vm_in3, Am_in2, tmc_s, tmp_s, tm_s, tm_prime_s

def main():
    print("=== Turning Sheet Populator (no milling prompts) ===")

    # Geometry
    l_full = get_float("Full workpiece length (in)")
    lw     = get_float("Working length lw (in)")
    da     = get_float("Starting diameter da (in)")
    db     = get_float("Overall final diameter db (in)")

    # Material
    mats = list(PRESETS.keys()) + ["custom"]
    material = pick_from_list("Workpiece material", mats)
    if material != "custom":
        density = PRESETS[material]["density"]
        ps_default = PRESETS[material]["ps"]
    else:
        density = get_float("Density (lb/in^3)", default=0.283)
        ps_default = get_float("Typical p_s (hp·min/in^3)", default=1.0)

    # Tool type (H/C/D)
    tool_code, _ = pick_from_list("Tool Type", TOOLING_CHOICES)

    # Weight from FULL length, then power
    Vstock_in3 = (math.pi / 4.0) * (da ** 2) * l_full
    Mstock_lb  = density * Vstock_in3
    print(f"\nEstimated stock weight: {Mstock_lb:.2f} lb  (volume {Vstock_in3:.2f} in^3)")

    Pm = get_float("Available power P_m (hp)", default=5.0)
    n_tool = get_n("Tooling constant n (0<n<1)", default=0.2)

    setup_hr  = get_float("Setup time per batch (hr)", default=0.25)
    load_s    = get_float("Load & unload time (s)", default=45)
    toolpos_s = get_float("Tool positioning time (s)", default=10)

    out_rows = []
    rough_selected = False
    finish_selected = False
    db_rough = None
    ps_shared = ps_default
    tprime_rough = 0.0
    tprime_finish = 0.0

    # Rough pass
    if input("Include ROUGH pass? [Y/n]: ").strip().lower() != "n":
        rough_selected = True
        op_r = pick_from_list("Rough pass: operation", OPERATIONS)
        db_rough = get_float("Rough pass final diameter db_rough (in) [>= final db]", default=db)
        db_rough = clamp_db_rough(db_rough, db, da)
        ps_shared = get_float("Rough pass: Specific cutting energy p_s (hp·min/in^3)", default=ps_default)
        vf_r = get_float("Rough pass: Rate of surface generation V_f (in^2/min)")

        vm, Am, tmc, tmp, tm, tm_prime = compute_pass_row(lw, da, db_rough, ps_shared, Pm, vf_r, n_tool, op_r)
        tprime_rough = tm_prime

        out_rows.append(make_row(tool_code, setup_hr, load_s, toolpos_s,
                                 lw, da, db_rough, vm, ps_shared, Pm, tmp, vf_r,
                                 Am, tmc, tm, tm_prime,
                                 "Rough", op_r, material,
                                 notes=f"Weight={Mstock_lb:.2f} lb"))

    # Finish pass
    if input("Include FINISH pass? [Y/n]: ").strip().lower() != "n":
        finish_selected = True
        op_f = pick_from_list("Finish pass: operation", OPERATIONS)
        vf_f = get_float("Finish pass: Rate of surface generation V_f (in^2/min)")

        # Use rough diameter as starting diameter if rough selected
        da_finish = db_rough if rough_selected and db_rough is not None else da

        vm, Am, tmc, tmp, tm, tm_prime = compute_pass_row(lw, da_finish, db, ps_shared, Pm, vf_f, n_tool, op_f)
        tprime_finish = tm_prime

        out_rows.append(make_row(tool_code, setup_hr, load_s, toolpos_s,
                                 lw, da_finish, db, vm, ps_shared, Pm, tmp, vf_f,
                                 Am, tmc, tm, tm_prime,
                                 "Finish", op_f, material,
                                 notes=f"Weight={Mstock_lb:.2f} lb (p_s & P_m reused)"))

    if not out_rows:
        print("No passes selected. Exiting.")
        return

    # ===== Costing =====
    print("\n=== Cost Inputs ===")
    cost_per_lb = get_float("Material cost per unit weight ($/lb)")
    hourly_rate = get_float("Operator hourly rate ($/hr)")
    num_parts   = get_float("Number of parts in batch", positive=True, default=1)

    material_cost_per_part = cost_per_lb * Mstock_lb
    setup_cost_per_part = (hourly_rate * setup_hr) / num_parts

    # Non-productive seconds per part: load/unload + toolpos (rough?) + toolpos (finish?)
    nonprod_seconds = load_s + (toolpos_s if rough_selected else 0) + (toolpos_s if finish_selected else 0)
    nonprod_cost_per_part = hourly_rate * (nonprod_seconds / 3600.0)

    # Machining cost per part using corrected times t_m'
    total_machining_seconds = (tprime_rough if rough_selected else 0.0) + (tprime_finish if finish_selected else 0.0)
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
        for r in out_rows:
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
