# BMS Wiring Guide - EW11A to HRUC-Plus 3 VL
## Complete Wiring Instructions for Modbus RS485 Connection

**Date Created:** January 20, 2026
**Source:** Official pinout from Vent-Axia UK (via Erik Van den Bergh)
**Pinout Diagram:** `BMS_PIN_mapping.png`

---

## Quick Reference

```
HRUC BMS RJ12 (J20)          EW11A Terminal
─────────────────────        ────────────────────
Pin 6 (+5V)    ───────────── VCC
Pin 3 (MOD A)  ───────────── A
Pin 4 (MOD B)  ───────────── B
Pin 5 (GND)    ───────────── GND
```

---

## BMS RJ12 Connector (J20) - Complete Pinout

The BMS connector is a **6P6C RJ12 jack** located on the HRUC control board.

| Pin | Signal | Description | Wire Color (typical) | Connect to EW11A |
|-----|--------|-------------|---------------------|------------------|
| 1 | P24VF9 | +24V DC (fused 500mA) | Red | ⚠️ **DO NOT USE** |
| 2 | GND | Ground | Black | (alternative GND) |
| 3 | MOD A | RS485 Data+ | Green/White | **A** |
| 4 | MOD B | RS485 Data- | Green | **B** |
| 5 | GND | Ground | Black/Yellow | **GND** |
| 6 | P5VF10 | +5V DC (fused 500mA) | Orange | **VCC** |

### Pin Numbering Reference

```
Looking at RJ12 jack opening (clip facing down):

        ┌─────────────────────────┐
        │  1   2   3   4   5   6  │
        │ 24V GND  A   B  GND +5V │
        └──────────┬──────────────┘
                   │
                 clip

Pin 1 = leftmost (24V - DO NOT USE for EW11A!)
Pin 6 = rightmost (+5V - safe for EW11A)
```

---

## Power Supply Warning

### EW11A Specifications
- **Input Voltage:** 5-18V DC
- **Power Consumption:** Max 5W (~100-150mA typical)

### Power Pin Selection

| BMS Pin | Voltage | For EW11A |
|---------|---------|-----------|
| Pin 1 | 24V | ❌ **DANGER** - Exceeds 18V max, will damage EW11A! |
| Pin 6 | 5V | ✅ **SAFE** - Within 5-18V range |

**IMPORTANT:** Only use Pin 6 (+5V) for powering the EW11A!

---

## Wiring Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     HRUC-Plus 3 VL Control Board                │
│                                                                 │
│   BMS Connector (J20 - RJ12 6P6C)                              │
│   ┌─────────────────────────┐                                  │
│   │  1   2   3   4   5   6  │                                  │
│   │ 24V GND  A   B  GND +5V │                                  │
│   └──┬───┬───┬───┬───┬───┬──┘                                  │
│      │   │   │   │   │   │                                     │
│      X   X   │   │   │   │    (X = not connected)              │
│              │   │   │   │                                     │
└──────────────┼───┼───┼───┼─────────────────────────────────────┘
               │   │   │   │
               │   │   │   └──────────┐
               │   │   │              │
               │   │   └──────────┐   │
               │   │              │   │
               │   └──────────┐   │   │
               │              │   │   │
               │   ┌──────────┼───┼───┼──────────────────────────┐
               │   │          │   │   │      EW11A Gateway       │
               │   │    ┌─────┴───┴───┴─────┐                    │
               │   │    │  A   B  GND  VCC  │  RS485 Terminal    │
               │   │    └──────────────────-┘                    │
               │   │                                             │
               └───┼─── Pin 3 (MOD A) ──────── A (Data+)         │
                   │                                             │
                   └─── Pin 4 (MOD B) ──────── B (Data-)         │
                                                                 │
                        Pin 5 (GND) ────────── GND               │
                                                                 │
                        Pin 6 (+5V) ────────── VCC               │
                                                                 │
                        ┌──────────────────┐                     │
                        │ Ethernet/WiFi    │──── Network         │
                        └──────────────────┘                     │
└────────────────────────────────────────────────────────────────┘
```

---

## Cable Construction Options

### Option 1: RJ12 Breakout Adapter (Recommended)
Buy an RJ12 to screw terminal adapter and connect wires to EW11A terminals.

**Pros:** Clean, reusable, no soldering
**Cons:** Additional cost (~€5-10)

### Option 2: Cut and Strip RJ12 Cable
Cut a standard RJ12 cable, strip wires, connect to EW11A.

**Wire Identification:**
1. Look at RJ12 plug with clip down
2. Count pins left to right (1-6)
3. Trace each wire to identify

**Common RJ12 Wire Colors (varies by manufacturer):**
| Pin | Common Colors |
|-----|---------------|
| 1 | White or Red |
| 2 | Black |
| 3 | Red or Green |
| 4 | Green or Yellow |
| 5 | Yellow or Black |
| 6 | Blue or Orange |

**IMPORTANT:** Always verify with multimeter! Colors are not standardized.

### Option 3: Custom Cable with Individual Wires
Use 4 individual wires with RJ12 plug on one end.

**Required Connections:**
- Pin 3 → EW11A A
- Pin 4 → EW11A B
- Pin 5 → EW11A GND
- Pin 6 → EW11A VCC

---

## EW11A Configuration

### Access Web Interface
```
URL: http://192.168.2.43
Login: Koky
Password: Aqwaqw05
```

### Required Settings

| Setting | Value | Location |
|---------|-------|----------|
| **Work Mode** | TCP Server | Network Settings |
| **Port** | 502 | Network Settings |
| **Protocol** | RTU over TCP | Serial Settings |
| **Baud Rate** | 115200 | Serial Settings |
| **Data Bits** | 8 | Serial Settings |
| **Parity** | None | Serial Settings |
| **Stop Bits** | 1 | Serial Settings |
| **Duplex** | Half-duplex | Serial Settings |
| **Gap Time** | 10ms | Serial Settings |
| **Modbus** | Enabled | Protocol Settings (optional) |

### Verification Checklist
- [ ] Power LED on (indicates 5V power working)
- [ ] Link LED on (indicates network connected)
- [ ] Web interface accessible
- [ ] Settings match table above

---

## RS485 Termination

### When to Use Terminator

The BMS board has a 120Ω terminator (R51) that can be enabled via jumper J4.

**Use terminator if:**
- EW11A is at the end of the RS485 bus
- Cable length > 10 meters
- Communication errors occur

**Skip terminator if:**
- Short cable (< 5 meters)
- EW11A has built-in termination enabled
- Communication works without it

### Enabling Terminator
1. Open HRUC unit
2. Locate jumper J4 on BMS board
3. Install jumper to enable 120Ω termination

---

## Testing Procedure

### Step 1: Physical Verification
```bash
# Verify EW11A is powered and on network
ping 192.168.2.43
```

### Step 2: Basic Modbus Test
```bash
cd /Users/peter.koval/Projects/comair_apk
python3 test_modbus_connection.py
```

### Step 3: Read Test Register
```python
from pymodbus.client import ModbusTcpClient

client = ModbusTcpClient('192.168.2.43', port=502)
client.connect()

# Read temperature register (slave ID 2)
result = client.read_input_registers(address=30100, count=1, slave=2)
print(f"Temperature: {result.registers[0] / 10}°C")

client.close()
```

### Step 4: Home Assistant Integration
Add to `configuration.yaml`:
```yaml
modbus:
  - name: comair_hruc
    type: tcp
    host: 192.168.2.43
    port: 502

    sensors:
      - name: "HRUC Intake Temperature"
        address: 30100
        slave: 2
        data_type: int16
        scale: 0.1
        unit_of_measurement: "°C"
        device_class: temperature
```

---

## Troubleshooting

### No Power to EW11A
- Check Pin 6 connection (should be +5V)
- Verify GND connection (Pin 5)
- Check F10 fuse on HRUC board (500mA)
- Measure voltage with multimeter

### Network Not Connecting
- Verify Ethernet cable connected
- Check EW11A IP settings
- Ping EW11A from computer

### Modbus Timeout Errors
- Verify slave ID is 2
- Check A/B wiring (not reversed)
- Verify baud rate 115200
- Try enabling terminator (J4)
- Check gap time is 10ms

### Wrong Data Values
- Verify register addresses
- Check data type (int16 vs uint16)
- Verify scaling factor (some values × 10)

---

## Power Consumption Calculation

### Available Power
- Pin 6 provides: 5V @ 500mA max = 2.5W

### EW11A Consumption
- Typical: ~100-150mA @ 5V = 0.5-0.75W
- Maximum: 5W (but this is at higher voltages)

### Margin
- Available: 2.5W
- Used: ~0.75W
- Margin: ~1.75W (sufficient)

---

## Safety Notes

1. **Power off HRUC before wiring** - Avoid electrical damage
2. **Double-check voltage** - 24V on Pin 1 will damage EW11A
3. **Verify pin numbering** - Count from correct end
4. **Use multimeter** - Confirm voltages before connecting
5. **Secure connections** - Loose wires cause intermittent issues

---

## Files Reference

| File | Purpose |
|------|---------|
| `BMS_PIN_mapping.png` | Official pinout diagram from Vent-Axia |
| `modbus_tcp_config.yaml` | Home Assistant Modbus configuration |
| `test_modbus_connection.py` | Python test script |
| `MVHR-BMS Modbus Map.pdf` | Complete register documentation |

---

## Contact Information

### Vent-Axia Support
- **Erik Van den Bergh** - Continuous Improvement Manager & HR, Vent-Axia B.V.
- Email: Erik.VandenBergh@vent-axia.nl
- Phone: +31(0) 626 646 549

### Project Owner
- **Peter Kováľ**
- Email: kokysyn@gmail.com
- Phone: +421 908 953 447

---

**Document Version:** 1.0
**Last Updated:** January 20, 2026
**Status:** Ready for Implementation
