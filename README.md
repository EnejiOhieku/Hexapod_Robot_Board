# 18-DOF Hexapod Robot Controller Board

[![KiCad Version](https://img.shields.io/badge/KiCad-10.0-blue.svg)](https://kicad.org)
[![ERC Status](https://img.shields.io/badge/ERC-Passed%20(0%20errors)-brightgreen.svg)]()
[![DRC Status](https://img.shields.io/badge/DRC-Passed%20(0%20violations)-brightgreen.svg)]()
[![Layers](https://img.shields.io/badge/Layers-4%20Layers-orange.svg)]()
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A fabrication-ready, 4-layer robotics controller PCB designed for an **18-DOF Hexapod Robot**. The board features an **ESP32-S3** microcontroller, dual **PCA9685** 16-channel PWM extenders (18 leg servos + 6 auxiliary PWM channels), an integrated **2S LiPo fast Type-C charger (TP5100)**, a dedicated **5V/3A buck converter (MP1584)** for high-current servo actuation, and battery voltage telemetry.

---

## 3D Board Previews

<p align="center">
  <img src="fabrication/Hexapod_Robot_Board_3D.png" alt="Hexapod Board 3D Perspective" width="85%" />
</p>

<p align="center">
  <img src="fabrication/Hexapod_Robot_Board_Top.png" alt="Top View" width="48%" />
  <img src="fabrication/Hexapod_Robot_Board_Bottom.png" alt="Bottom View" width="48%" />
</p>

---

## System Architecture

```mermaid
flowchart TD
    USB["USB Type-C (5V Fast Charge)"] --> U2["TP5100 2S LiPo Charger (8.4V / 1.5A)"]
    BAT["2S LiPo Battery (7.4V - 8.4V) via XT30"] --> SW_PWR["Main Power Switch"]
    U2 --> BAT
    SW_PWR --> BUCK["MP1584 5V / 3A Buck Regulator"]
    SW_PWR --> DIV["Battery Voltage Divider (R_DIV1 / R_DIV2)"]
    SW_PWR --> LDO["AP2112K 3.3V / 600mA Low-Noise LDO"]
    
    BUCK --> V_SERVO["V_SERVO Plane (In2.Cu)"]
    V_SERVO --> SERVOS["18x Servo Headers (6 Legs x 3 Joints) + 6x AUX PWM"]
    
    LDO --> V33["+3V3 MCU PDN (F.Cu)"]
    V33 --> U1["ESP32-S3-WROOM-1 MCU"]
    V33 --> U3["PCA9685 16-Ch PWM Controller (Addr: 0x40)"]
    V33 --> U4["PCA9685 16-Ch PWM Controller (Addr: 0x41)"]
    
    U1 -- "I2C (SDA: GPIO4, SCL: GPIO5)" --> U3
    U1 -- "I2C (SDA: GPIO4, SCL: GPIO5)" --> U4
    U1 -- "ADC (GPIO1)" --> DIV
    U1 -- "GPIO2 (CHG_STAT), GPIO3 (CHG_PG)" --> U2
    
    U3 -- "Channels 0-15" --> SERVOS
    U4 -- "Channels 0-7" --> SERVOS
```

---

## Key Hardware Features

- **Microcontroller**: ESP32-S3-WROOM-1 (Dual-core Xtensa LX7 @ 240MHz, 2.4GHz Wi-Fi 4, BLE 5, 8MB Flash).
- **Actuation**: Dual PCA9685 12-bit PWM controllers over dedicated I2C bus (`0x40`, `0x41`), capable of controlling 18 leg servos and 6 auxiliary peripherals.
- **Power Management**:
  - **Input**: 2S LiPo battery (7.4V nominal) via horizontal AMASS XT30PW connector.
  - **Charging**: Onboard TP5100 fast switching charger (8.4V CV cutoff, ~1.5A charge rate) with Type-C input and dual LED indicators.
  - **Servo Power**: Dedicated MP1584 buck regulator delivering 5.0V @ 3A continuous (4A peak) into an internal copper power plane.
  - **Logic Power**: AP2112K-3.3V LDO protected with Schottky reverse isolation and 220µF bulk capacitance to prevent brownouts during sudden motor stalls.
  - **Monitoring**: Precision 1% resistor divider (100kΩ / 33kΩ) connected to ESP32-S3 ADC (GPIO1).
- **Physical Specifications**:
  - **Size**: 100.0 mm × 80.0 mm.
  - **Mounting**: 4× M3 mounting holes at `(6.0, 6.0)`, `(94.0, 6.0)`, `(6.0, 74.0)`, and `(94.0, 74.0)`.
  - **Stackup**: 4 Layers (`F.Cu` Signals/PDN, `In1.Cu` Solid GND, `In2.Cu` V_SERVO high-current plane, `B.Cu` Signals).

---

## Servo Channel Mapping

| Leg / Joint | Header Ref | Controller | Channel | I2C Addr |
| :--- | :--- | :--- | :--- | :--- |
| **Right Front (RF) Coxa** | `J_L1_C` | PCA9685 #1 | PWM 0 | `0x40` |
| **Right Front (RF) Femur** | `J_L1_F` | PCA9685 #1 | PWM 1 | `0x40` |
| **Right Front (RF) Tibia** | `J_L1_T` | PCA9685 #1 | PWM 2 | `0x40` |
| **Right Middle (RM) Coxa** | `J_L2_C` | PCA9685 #1 | PWM 3 | `0x40` |
| **Right Middle (RM) Femur** | `J_L2_F` | PCA9685 #1 | PWM 4 | `0x40` |
| **Right Middle (RM) Tibia** | `J_L2_T` | PCA9685 #1 | PWM 5 | `0x40` |
| **Right Rear (RR) Coxa** | `J_L3_C` | PCA9685 #1 | PWM 6 | `0x40` |
| **Right Rear (RR) Femur** | `J_L3_F` | PCA9685 #1 | PWM 7 | `0x40` |
| **Right Rear (RR) Tibia** | `J_L3_T` | PCA9685 #1 | PWM 8 | `0x40` |
| **Left Front (LF) Coxa** | `J_L4_C` | PCA9685 #1 | PWM 9 | `0x40` |
| **Left Front (LF) Femur** | `J_L4_F` | PCA9685 #1 | PWM 10 | `0x40` |
| **Left Front (LF) Tibia** | `J_L4_T` | PCA9685 #1 | PWM 11 | `0x40` |
| **Left Middle (LM) Coxa** | `J_L5_C` | PCA9685 #1 | PWM 12 | `0x40` |
| **Left Middle (LM) Femur** | `J_L5_F` | PCA9685 #1 | PWM 13 | `0x40` |
| **Left Middle (LM) Tibia** | `J_L5_T` | PCA9685 #1 | PWM 14 | `0x40` |
| **Left Rear (LR) Coxa** | `J_L6_C` | PCA9685 #1 | PWM 15 | `0x40` |
| **Left Rear (LR) Femur** | `J_L6_F` | PCA9685 #2 | PWM 0 | `0x41` |
| **Left Rear (LR) Tibia** | `J_L6_T` | PCA9685 #2 | PWM 1 | `0x41` |
| **Auxiliary PWM 1** | `J_AUX1` | PCA9685 #2 | PWM 2 | `0x41` |
| **Auxiliary PWM 2** | `J_AUX2` | PCA9685 #2 | PWM 3 | `0x41` |
| **Auxiliary PWM 3** | `J_AUX3` | PCA9685 #2 | PWM 4 | `0x41` |
| **Auxiliary PWM 4** | `J_AUX4` | PCA9685 #2 | PWM 5 | `0x41` |
| **Auxiliary PWM 5** | `J_AUX5` | PCA9685 #2 | PWM 6 | `0x41` |
| **Auxiliary PWM 6** | `J_AUX6` | PCA9685 #2 | PWM 7 | `0x41` |

---

## Manufacturing Deliverables

All fabrication files are available in the [`fabrication/`](fabrication/) directory:

- **Gerbers & Drill**: [`fabrication/Hexapod_Robot_Board-gerbers.zip`](fabrication/Hexapod_Robot_Board-gerbers.zip)
- **Pick & Place (CPL)**: [`fabrication/Hexapod_Robot_Board-cpl.csv`](fabrication/Hexapod_Robot_Board-cpl.csv)
- **Assembly BOM (JLCPCB)**: [`fabrication/Hexapod_Robot_Board-bom-jlcpcb.csv`](fabrication/Hexapod_Robot_Board-bom-jlcpcb.csv)
- **Full Schematic BOM**: [`fabrication/Hexapod_Robot_Board-bom.csv`](fabrication/Hexapod_Robot_Board-bom.csv)
- **3D Mechanical Model**: [`fabrication/Hexapod_Robot_Board.step`](fabrication/Hexapod_Robot_Board.step)
- **Printable Schematic**: [`fabrication/Hexapod_Robot_Board-schematic.pdf`](fabrication/Hexapod_Robot_Board-schematic.pdf)

---

## Verification & Compliance

- **Electrical Rules Check (ERC)**: Passed with 0 errors, 0 warnings (`Hexapod_Robot_Board-erc.rpt`).
- **Design Rules Check (DRC)**: Passed with 0 violations, 0 unconnected items (`Hexapod_Robot_Board-drc.rpt`).
- **Standard**: Follows JLCPCB 4-Layer 6mil rules (0.15mm clearance, 0.20mm track width, 0.30mm via drill).
