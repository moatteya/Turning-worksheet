# Turning Worksheet Automation

This project provides a Python script (`turning_sheet.py`) that automates the generation of machining parameters and costs for **turning operations** (rough and finish passes).  
The script prompts the user for workpiece, tool, and machining data, then calculates times, volumes, and costs, outputting results into a CSV file matching a standard machining worksheet format.

---

## ✨ Features
- Supports **rough** and **finish** turning passes (optional).
- Calculates:
  - Workpiece stock weight from material density and geometry.
  - Material removal volume (`V_m`) and surface area (`A_m`).
  - Recommended machining time (`t_mc`) from user-input surface generation rate (`V_f`).
  - Maximum power-limited machining time (`t_mp`) from available spindle power (`P_m`).
  - Corrected machining time (`t_m`) using the tool wear constant `n`.
  - Corrected machining time with tool travel (`t_m'`).
- Handles different tool types: HSS (H), Carbide (C), Diamond/CBN/PCD (D).
- Outputs all results into `turning_sheet.csv` with the same column structure as standard worksheets.
- Calculates **cost per part**:
  - Material cost (based on $/lb).
  - Setup cost (spread across batch size).
  - Non-productive time (load/unload, tool positioning).
  - Machining time cost.

---

## 📦 Requirements
- Python 3.8+
- Standard library only (`math`, `csv`, `datetime`) → no extra installs needed.

---

## ▶️ Usage
1. Clone this repository:
   ```bash
   git clone git@github.com:moatteya/Turning-worksheet.git
   cd Turning-worksheet
