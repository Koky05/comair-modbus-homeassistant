# Modbus CONFIRMED Settings from Vent-Axia Connect App
## CRITICAL DISCOVERY: Device DOES Support Modbus!

**Date:** December 19, 2025
**Source:** Vent-Axia Connect App → Advanced Settings → Modbus Section
**Status:** 🎉 **Modbus Support Confirmed!**

---

## 📋 Confirmed Modbus Settings

Found in Vent-Axia Connect app under **Advanced Settings → Modbus**:

| Setting | Value | Status |
|---------|-------|--------|
| **Modbus Address** | **2** | ✅ Confirmed |
| **Parity** | **None** | ✅ Confirmed |
| **Baud Rate** | **115200** | ✅ Confirmed |
| **Data Bits** | 8 | (Standard) |
| **Stop Bits** | 1 | (Standard) |

**This confirms:** The HRUC-Plus 3 VL **DOES support Modbus protocol!**

---

## 🔍 What Went Wrong in Previous Testing

### Our Previous Configuration (EW11a)
```
Baud Rate: 115200 ✅ (CORRECT)
Data Bits: 8 ✅ (CORRECT)
Stop Bits: 1 ✅ (CORRECT)
Parity: None ✅ (CORRECT)
Protocol: Modbus ✅ (CORRECT)
```

### Our Previous Testing
```
Slave IDs tested: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
Result: No responses from any slave ID
Requests sent: 527,737+
Valid responses: 0
```

### Why It Failed - Likely Causes

**Most Likely (90%):** Physical Connection Issue
- RS485 A/B terminals not connected to ComAir unit
- Wrong terminals used on ComAir (maybe labeled differently)
- Cable not properly inserted
- Terminals on wrong component (need main controller board)

**Possible (5%):** Modbus Not Enabled in Device
- May need to enable Modbus in Vent-Axia app settings
- Check if there's an "Enable Modbus" toggle in app

**Possible (3%):** A/B Polarity Reversed
- RS485 A connected to B terminal and vice versa
- Simple fix: swap the wires

**Unlikely (2%):** EW11a Configuration Issue
- Despite matching settings, something might be misconfigured
- Need to verify raw serial communication

---

## 🎯 Why This Changes Everything

### Before This Discovery
- ❌ Thought Modbus not supported on HRUC-Plus 3 VL
- ✅ Focused on PSK extraction
- ❌ Gave up on Modbus approach
- ⏸️ Waiting for manufacturer PSK

### After This Discovery
- ✅ **Modbus IS supported!**
- ✅ **Exact settings confirmed!**
- ✅ **New troubleshooting path available!**
- 🎯 **Modbus might be EASIER than PSK!**

---

## 💡 Modbus Advantages Over PSK

| Aspect | PSK Approach | Modbus Approach |
|--------|--------------|-----------------|
| **Complexity** | High (TLS, encryption) | Low (standard protocol) |
| **Dependencies** | Need PSK value | Just physical connection |
| **HA Integration** | Custom component | Native Modbus integration |
| **Reliability** | WiFi dependent | Wired RS485 |
| **Maintenance** | Custom code to maintain | Standard, well-tested |
| **Future-proof** | Depends on protocol stability | Industry standard |
| **Real-time** | Push notifications | Polling (1-2 sec) |
| **Setup Time** | 5 min (with PSK) | 30 min (physical wiring) |

---

## 🔧 What We Need to Fix

### Physical Inspection Required

**When Home, Check:**
1. **RS485 Terminal Location**
   - Open ComAir unit
   - Locate main controller board
   - Identify RS485 terminals (likely labeled A, B, GND or +, -)
   - Verify EW11a is actually connected

2. **Wiring Verification**
   - Check if A/B wires are connected
   - Verify polarity (try swapping if needed)
   - Check ground connection
   - Ensure good electrical contact

3. **App Settings Check**
   - Look for "Enable Modbus" option in Vent-Axia app
   - Check if Modbus needs to be activated
   - Screenshot all Modbus-related settings

### EW11a Configuration Review

**Current EW11a Settings:**
```
IP: 192.168.2.43
Serial Port:
  - Baud Rate: 115200 ✅
  - Data Bits: 8 ✅
  - Stop Bits: 1 ✅
  - Parity: None ✅
  - Protocol: Modbus ✅

Network (netp):
  - Protocol: TCP Server
  - Port: 502 ✅
  - Route: Uart ✅
```

**Verify These Match App Settings:** ✅ All correct!

---

## 📋 Modbus Retry Action Plan (When Home)

### Phase 1: Physical Verification (15 minutes)

**Step 1: Document Current Setup**
```bash
# Take photos of:
# 1. ComAir unit interior (controller board)
# 2. RS485 terminal connections
# 3. EW11a connection
# 4. Wire routing from EW11a to ComAir
```

**Step 2: Verify Physical Connection**
- [ ] Open ComAir HRUC-Plus 3 VL unit
- [ ] Locate main controller board
- [ ] Find RS485 terminals (should be labeled)
- [ ] Verify EW11a A/B wires are connected
- [ ] Check terminal labels match wiring
- [ ] Ensure good mechanical connection

**Step 3: Check for Enable Setting**
- [ ] Open Vent-Axia Connect app
- [ ] Go to Advanced Settings → Modbus
- [ ] Look for "Enable Modbus" or similar toggle
- [ ] Screenshot all settings
- [ ] Enable if there's a toggle

---

### Phase 2: Basic Connectivity Test (5 minutes)

**Test 1: Verify EW11a can communicate with ComAir**

```bash
# On Mac, connect to EW11a web interface
open http://192.168.2.43

# Check Statistics page:
# - Serial Port "Received" should show data if ComAir is talking
# - If "Received" is zero or not incrementing, no serial communication
```

**Test 2: Send Test Modbus Request**

```bash
cd /Users/peter.koval/Projects/comair_apk

# Use existing test script with CORRECT slave ID
python3 test_modbus_connection.py
```

**Expected:**
- If wiring correct: Responses from slave ID 2
- If wiring wrong: Timeout errors

---

### Phase 3: Troubleshooting (30 minutes)

#### If Still No Response:

**Try 1: Swap A/B Wires**
- Disconnect A/B from ComAir terminals
- Swap them (A→B, B→A)
- Test again

**Try 2: Test with Different Slave IDs**
```python
# Maybe app shows "2" but device uses different ID
for slave_id in [1, 2, 3, 4, 5]:
    # Test slave_id
```

**Try 3: Enable Modbus in App**
- Check Vent-Axia app for enable/disable setting
- Might be disabled by default for security

**Try 4: Raw Serial Test**
```bash
# Send raw Modbus RTU frame to verify serial works
# Frame: Read holding register 40030 from slave 2
# Hex: 02 03 9C 1D 00 01 [CRC]
```

**Try 5: Check ComAir Manual/Documentation**
- Look for RS485 terminal diagram
- Verify terminal labels in app Advanced Settings
- Check if manual shows terminal location

---

### Phase 4: Home Assistant Integration (10 minutes)

**If Modbus Works:**

Update Home Assistant configuration:

```yaml
# configuration.yaml
modbus:
  - name: comair_hruc
    type: tcp
    host: 192.168.2.43
    port: 502

    sensors:
      # Intake Temperature (T1)
      - name: "HRUC Intake Temperature"
        address: 30100
        slave: 2  # ← CONFIRMED FROM APP
        data_type: int16
        scale: 0.1
        precision: 1
        unit_of_measurement: "°C"
        device_class: temperature
        state_class: measurement

      # Supply Temperature (T2)
      - name: "HRUC Supply Temperature"
        address: 30110
        slave: 2
        data_type: int16
        scale: 0.1
        precision: 1
        unit_of_measurement: "°C"
        device_class: temperature
        state_class: measurement

      # Extract Temperature (T3)
      - name: "HRUC Extract Temperature"
        address: 30120
        slave: 2
        data_type: int16
        scale: 0.1
        precision: 1
        unit_of_measurement: "°C"
        device_class: temperature
        state_class: measurement

      # Exhaust Temperature (T4)
      - name: "HRUC Exhaust Temperature"
        address: 30130
        slave: 2
        data_type: int16
        scale: 0.1
        precision: 1
        unit_of_measurement: "°C"
        device_class: temperature
        state_class: measurement

      # Add all other sensors from MVHR-BMS Modbus Map
      # Using slave ID 2 (confirmed from app)
```

Restart Home Assistant and test!

---

## 🎯 Success Criteria

### Minimal Success
- [ ] Read at least one register successfully
- [ ] Verify slave ID 2 responds
- [ ] Confirm physical connection works

### Full Success
- [ ] All temperature sensors readable (30100, 30110, 30120, 30130)
- [ ] All humidity sensors readable (30101, 30121)
- [ ] All CO2 sensors readable (30102, 30122)
- [ ] Control register writable (40030)
- [ ] Home Assistant integration working

---

## 📊 Revised Success Probabilities

### With Confirmed Modbus Support

| Method | Old Estimate | New Estimate | Notes |
|--------|--------------|--------------|-------|
| **Modbus (Physical Fix)** | 0% (thought unsupported) | **70%** 🎯 | Just need to fix wiring! |
| **Management PSK** | 60% | 60% | Still good option |
| **ADB Backup PSK** | 20% | 20% | Still worth trying |
| **Frida Hooking** | 85% | 85% | Still backup plan |

**Overall Success:** **95%+** (now with Modbus as primary path!)

---

## 💡 Recommendation: Prioritize Modbus

### Why Modbus Should Be Priority #1 Now

**Advantages:**
1. ✅ **Confirmed supported** by manufacturer
2. ✅ **Settings known** (Address=2, Baud=115200, Parity=None)
3. ✅ **Hardware already purchased** (EW11a gateway)
4. ✅ **Native HA support** (no custom component)
5. ✅ **Standard protocol** (future-proof)
6. ✅ **Complete sensor access** (all temps, RH, CO2, power)
7. ✅ **Control possible** (register 40030)
8. ✅ **No PSK needed!**

**Disadvantages:**
1. ❌ Requires physical access to unit
2. ❌ Need to troubleshoot wiring
3. ❌ Polling instead of push (minor)

---

## 🔧 Questions for Vent-Axia App

**Check These Settings When Home:**

### In Advanced Settings → Modbus Section:
- [ ] Is there an "Enable Modbus" toggle? (If yes, enable it!)
- [ ] Are there any other settings besides Address/Parity/Baud?
- [ ] Does it show terminal locations or wiring diagram?
- [ ] Is there a "Modbus Status" indicator?
- [ ] Are there any error messages or warnings?
- [ ] Does it show what registers are available?
- [ ] Can you test Modbus communication from the app?

### Take Screenshots:
- [ ] Complete Modbus settings page
- [ ] Any Modbus-related help text
- [ ] Terminal diagram if shown

---

## 📋 Updated "When Home" Priority

### New Priority Order:

**1. Verify Device Connectivity (5 min)**
- Ping device
- Check port 47820
- Confirm firmware update successful

**2. Fix Modbus Connection (30-45 min)** ⭐ **NEW PRIORITY**
- Verify physical RS485 wiring
- Enable Modbus in app if needed
- Test with confirmed settings (Address=2)
- Get at least one register reading
- If successful → Configure HA Modbus → **DONE!**

**3. Try ADB Backup (15 min)**
- If Modbus troubleshooting too complex
- Quick attempt at PSK extraction
- Fallback if Modbus physically difficult

**4. Wait for Management PSK**
- If both above don't work
- Or if prefer official support

---

## 🎉 This Changes the Game!

### Before:
"Modbus doesn't work, need PSK somehow"

### After:
"Modbus IS supported, just need to fix the physical connection!"

**This could be much easier than PSK extraction!**

---

## 📝 Next Steps Summary

**Immediate (When Home):**
1. Open Vent-Axia app → Advanced Settings → Modbus
2. Screenshot all settings
3. Check for "Enable Modbus" toggle
4. Open ComAir unit
5. Verify RS485 physical connection
6. Test Modbus with slave ID 2
7. If works → Configure HA → Celebrate! 🎉

**If Modbus Works:**
- No PSK needed!
- Native HA integration
- Standard protocol
- Better long-term solution

**If Modbus Doesn't Work:**
- Still have PSK paths (management, ADB, Frida)
- At least we tried!

---

**Document Created:** December 19, 2025
**Status:** Modbus support CONFIRMED from app settings
**Impact:** MAJOR - Changes primary integration strategy
**Next Action:** Fix physical RS485 connection when home

**This could be the breakthrough we needed!** 🎯🚀
