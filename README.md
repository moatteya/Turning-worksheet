# Turning & Milling Worksheet Populator

This Python script automates the population of a machining worksheet for **turning, facing, boring, drilling, threading, cutoff, and milling operations**.  
It calculates the geometry, cutting times, and costs per part, and outputs rows in a CSV (`turning_sheet.csv`) that match the column headers of your provided sheet.

---

## Features

- **Material presets** for density and default cutting energy \(p_s\) (steel, aluminum, titanium, etc.), or custom values.
- Supports **two passes**:
  - **Rough pass**
  - **Finish pass** (automatically starts from the rough diameter if applicable)
- **Per-operation formulas**:
  - **Turn/Thread**  
    - \( A_m = \pi l_w d_b \)  
    - \( V_m = \tfrac{\pi}{4} l_w (d_a^2 - d_b^2) \)
  - **Bore/Drill/Tap/Ream**  
    - \( A_m = \pi l_w d_a \)  
    - \( V_m = \tfrac{\pi}{4} l_w (d_b^2 - d_a^2) \)
  - **Face/Thread**  
    - \( A_m = \tfrac{\pi}{2} d_a (d_a - d_b) \)  
    - \( V_m = \tfrac{\pi}{2} l_w d_a (d_a - d_b) \)
  - **Milling**  
    - \( A_m = l_w d_a \)  
    - \( V_m = l_w d_a d_b \)
- Cutting time calculations:
  - \( t_{mp} = \dfrac{60 p_s V_m}{P_m} \)  
  - \( t_{mc} = \dfrac{60 A_m}{V_f} \) (always from user-supplied surface generation rate \(V_f\))  
  - Tool wear correction using constant \(n\) (entered by user)  
  - Tool travel correction: adds **5.4 s** for turning, facing, boring, cutoff
- **Costing**:
  - Material cost per part (density × volume × $/lb)
  - Setup cost (distributed over parts in the batch)
  - Non-productive cost (load/unload + tool positioning)
  - Machining cost (based on corrected machining times)
  - Final **total cost per part**

---

## Usage

1. Install Python 3.  
2. Save the script as `turning_sheet.py`.
3. Run in terminal:
   ```bash
   python turning_sheet.py
4. Answer the propmts.
5. Load the CSV with the filled worksheet.