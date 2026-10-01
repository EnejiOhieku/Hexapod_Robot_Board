# Hexapod Robot Board Automation & Engineering Scripts

This directory contains standalone Python automation scripts for schematic generation, 4-layer PCB routing, clearance optimization, and manufacturing export for the **18-DOF Hexapod Robot Controller Board (Rev 2.0)**.

---

## 📜 Script Manifest

### 1. `export_fabrication.py`
The unified manufacturing export pipeline. Automatically executes `kicad-cli` and `pcbnew` to:
- Run full **ERC** and **DRC** audits with reports placed into `reports/`.
- Export all 11 RS-274X Gerber layers and separate PTH/NPTH Excellon drill files to `fabrication/gerbers/` and compile them into `Hexapod_Robot_Board-gerbers.zip`.
- Generate SMT Pick-and-Place (CPL) files (`Hexapod_Robot_Board-cpl-jlcpcb.csv` and standard `pos.csv`).
- Generate categorized Bill of Materials (BOM) with pre-assigned LCSC part numbers.
- Export high-precision 3D mechanical STEP model (`Hexapod_Robot_Board.step`).
- Export vector schematic PDF (`Hexapod_Robot_Board_Schematic.pdf`).
- Export PCB stackup and geometric statistics (`Hexapod_Robot_Board-stats.txt`).

**Usage:**
```bash
/home/peacemaker/.local/share/kicad-mcp-server/.venv/bin/python scripts/export_fabrication.py
```

---

### 2. `run_final_perfect_route.py`
The deterministic, multi-layer routing solver:
- Enforces Layer 3 (`In2.Cu`) as a dedicated power plane in the Specctra DSN export.
- Pre-routes all high-current buck switching loops, servo daisy chains, and SMD power vias to eliminate loop inductance.
- Invokes Freerouting for multi-pass maze routing of signal traces with strict $45^\circ$ mitered geometry.
- Applies clean layer-transition patches for U7 (MPU-6050) ground escape and I2C routing.
- Confirms **0 DRC violations** and **0 unconnected items**.

**Usage:**
```bash
/home/peacemaker/.local/share/kicad-mcp-server/.venv/bin/python scripts/run_final_perfect_route.py
```

---

### 3. `route_power_primitives.py`
Helper library containing parametric copper primitives:
- Wide trace generation for switching nodes (`BUCK_SW_L`, `BUCK_SW_R`).
- High-current via clusters (0.4mm drill / 0.8mm annular ring) for low-impedance plane stitching.
- Reversible USB Type-C `VBUS` power bridging tracks.

---

### 4. `generate_perfect_schematic.py`
Python schematic generator script:
- Generates `Hexapod_Robot_Board.kicad_sch` with symbols snapped to standard 1.27mm / 2.54mm grid.
- Configures ESP32-S3-WROOM-1U, dual XL4015 buck regulators, PCA9685 PWM drivers, and MPU-6050 IMU.
- Validates 0 ERC errors.
