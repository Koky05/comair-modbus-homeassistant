# ComAir HRUC-Plus 3 VL - Modbus Integration Analysis

## Connection Details

**Protocol:** RS485 MODBUS-RTU / TCP (Half duplex)
- **Baud Rate:** 115200/N (configurable via app)
- **Device Address:** 2 (configurable via app)
- **Endianness:** Big Endian (MODBUS standard)
- **Physical Interface:** RS485 on circuit board inside unit

## Hardware Requirements

To connect via Modbus, you will need:
1. **RS485 to USB adapter** (~€20-30)
   - Recommended: USB to RS485 converter with FTDI chip
   - Example: Waveshare USB to RS485 converter
2. **Physical access** to open the unit and connect to RS485 terminals
3. **Home Assistant** with Modbus integration (built-in)

## Available Input Registers (Read-Only)

These registers provide sensor data and status information:

### System Status
| Address | Description | Data Type | Unit | Property ID |
|---------|-------------|-----------|------|-------------|
| 30001 | Run time | uint16 | days | PID_RUN_TIME |
| 30002 | Service timer | uint16 | months | PID_SERVICE_TIMER_INTERVAL |
| 30003 | Filter timer | uint16 | months | PID_FILTER_TIMER_INTERVAL |
| 30004-05 | Faults present | uint32 | bitmask | PID_FAULTS_PRESENT |
| 30006-07 | Warnings present | uint32 | bitmask | PID_WARNINGS_PRESENT |
| 30008-09 | Notifications | uint32 | bitmask | PID_NOTIFICATIONS |
| 30010 | System power | uint16 | W | PID_SYSTEM_POWER |

### Output Status (Read-Only)
| Address | Description | Data Type |
|---------|-------------|-----------|
| 30020 | Attention Ventilation LED | bool |
| 30021 | Cooling enable output | bool |
| 30022 | Preheater enable output | bool |
| 30023 | Controlled cooling output | bool |
| 30024 | Controlled heating output | bool |

### Duct Temperatures & Sensors
| Address | Description | Data Type | Unit | Conversion |
|---------|-------------|-----------|------|------------|
| 30100 | Intake duct temperature (T1) | int16 | °C | Divide by 10 |
| 30101 | Intake duct RH | uint16 | % | Direct |
| 30102 | Intake duct CO2 | uint16 | PPM | Direct |
| 30110 | Supply duct temperature (T2) | int16 | °C | Divide by 10 |
| 30120 | Extract duct temperature (T3) | int16 | °C | Divide by 10 |
| 30121 | Extract duct RH | uint16 | % | Direct |
| 30122 | Extract duct CO2 | uint16 | PPM | Direct |
| 30130 | Exhaust duct temperature (T4) | int16 | °C | Divide by 10 |

### Zone Sensors (0-15)
Each zone has 4 registers with offset +10 per zone:
- **30200 + (zone × 10) + 0:** Zone Temperature (int16, °C x10)
- **30200 + (zone × 10) + 1:** Zone RH (uint16, %)
- **30200 + (zone × 10) + 2:** Zone CO2 (uint16, PPM)
- **30200 + (zone × 10) + 3:** Zone VOC (uint16, TBC)

Example:
- Zone 0: 30200-30203
- Zone 1: 30210-30213
- Zone 2: 30220-30223
- ...
- Zone 15: 30350-30353

## Available Holding Registers (Read/Write)

These registers allow control of the unit:

| Address | Description | Data Type | Unit | Notes |
|---------|-------------|-----------|------|-------|
| 40001-40010 | Virtual Inputs 1-10 | uint16 | - | PID_BMS_VIRTUAL_INPUT_VALUES_0-9 |
| 40020 | BMS Shutdown | uint16 | - | Magic code? |
| 40030 | User Override | uint16 | - | MSB=preset, LSB=minutes |
| 40040 | Machine Date - Year | uint16 | year | - |
| 40041 | Machine Date - Month/Day | uint16 | - | MSB=month, LSB=day |
| 40042 | Machine Time - hh:mm | uint16 | - | MSB=hour, LSB=minute |

### Critical Control Register: 40030 (User Override)

This is the most important register for controlling ventilation modes:
- **MSB (upper byte):** Preset/Mode selection
- **LSB (lower byte):** Duration in minutes

This likely maps to the ventilation modes we know from the TLS-PSK protocol:
- Mode 0: Auto
- Mode 1: Low
- Mode 2: Medium
- Mode 3: High
- Mode 4: Boost

## Comparison: Modbus vs TLS-PSK

| Feature | Modbus | TLS-PSK |
|---------|--------|---------|
| **Hardware needed** | RS485 adapter (~€25) | None |
| **Physical access** | Yes (open unit) | No |
| **Warranty impact** | Potentially void | None |
| **Setup complexity** | Medium (wiring) | High (PSK extraction) |
| **Protocol** | Standard Modbus | Proprietary Magna |
| **Home Assistant** | Native integration | Custom component |
| **Temperature sensors** | ✅ All 4 ducts + zones | ✅ All sensors |
| **Humidity sensors** | ✅ Intake + Extract + zones | ✅ All sensors |
| **CO2 sensors** | ✅ Intake + Extract + zones | ✅ All sensors |
| **Fan speed control** | ✅ Via register 40030 | ✅ Direct commands |
| **Mode control** | ✅ Via register 40030 | ✅ Direct commands |
| **Filter monitoring** | ✅ Register 30003 | ✅ Via status |
| **Service monitoring** | ✅ Register 30002 | ✅ Via status |
| **Fault detection** | ✅ Bitmask 30004-05 | ✅ Via status |
| **Real-time updates** | Polling only | Push notifications |
| **Network** | Serial/USB | WiFi (local) |
| **Reliability** | Very high | High |
| **Maintenance** | None | None |
| **Future-proof** | Yes (standard) | Depends on app |

## Advantages of Modbus Approach

1. **Standard Protocol:** Industry-standard, well-documented
2. **No PSK Required:** Bypasses authentication completely
3. **Native HA Support:** Built-in Modbus integration in Home Assistant
4. **Complete Access:** All sensors and controls available
5. **Reliable:** Direct wired connection, no WiFi dependency
6. **Well-Tested:** Modbus is battle-tested in industrial applications

## Disadvantages of Modbus Approach

1. **Hardware Cost:** Need to buy RS485 adapter (~€25)
2. **Physical Installation:** Must open unit and wire adapter
3. **Warranty Concerns:** Opening unit may void warranty
4. **Polling Only:** No push notifications (need to poll regularly)
5. **Wiring Complexity:** Need to route USB cable from unit to HA server

## Recommended Next Steps

### Option A: Proceed with Modbus (Recommended)
1. **Purchase RS485 adapter** - USB to RS485 converter
2. **Locate RS485 terminals** in the unit (check manual or ask Robbert)
3. **Connect adapter** to RS485 A/B terminals and ground
4. **Configure Home Assistant** Modbus integration
5. **Test connection** and verify register reads
6. **Create entities** for all sensors and controls

### Option B: Continue PSK Extraction
1. Wait for new app release (2-3 months)
2. Try extracting PSK from new app version
3. Use existing TLS-PSK integration

### Option C: Hybrid Approach
1. Use Modbus for reliable monitoring
2. Keep mobile app for occasional manual control
3. Best of both worlds without PSK extraction

## Home Assistant Configuration Preview

```yaml
# configuration.yaml
modbus:
  - name: comair_hruc
    type: serial
    port: /dev/ttyUSB0
    baudrate: 115200
    bytesize: 8
    method: rtu
    parity: N
    stopbits: 1

    sensors:
      # Intake duct temperature
      - name: "HRUC Intake Temperature"
        address: 30100
        slave: 2
        data_type: int16
        scale: 0.1
        precision: 1
        unit_of_measurement: "°C"
        device_class: temperature
        state_class: measurement

      # Supply duct temperature
      - name: "HRUC Supply Temperature"
        address: 30110
        slave: 2
        data_type: int16
        scale: 0.1
        precision: 1
        unit_of_measurement: "°C"
        device_class: temperature
        state_class: measurement

      # Extract duct temperature
      - name: "HRUC Extract Temperature"
        address: 30120
        slave: 2
        data_type: int16
        scale: 0.1
        precision: 1
        unit_of_measurement: "°C"
        device_class: temperature
        state_class: measurement

      # Exhaust duct temperature
      - name: "HRUC Exhaust Temperature"
        address: 30130
        slave: 2
        data_type: int16
        scale: 0.1
        precision: 1
        unit_of_measurement: "°C"
        device_class: temperature
        state_class: measurement

      # Intake RH
      - name: "HRUC Intake Humidity"
        address: 30101
        slave: 2
        data_type: uint16
        unit_of_measurement: "%"
        device_class: humidity
        state_class: measurement

      # Extract RH
      - name: "HRUC Extract Humidity"
        address: 30121
        slave: 2
        data_type: uint16
        unit_of_measurement: "%"
        device_class: humidity
        state_class: measurement

      # Intake CO2
      - name: "HRUC Intake CO2"
        address: 30102
        slave: 2
        data_type: uint16
        unit_of_measurement: "ppm"
        device_class: carbon_dioxide
        state_class: measurement

      # Extract CO2
      - name: "HRUC Extract CO2"
        address: 30122
        slave: 2
        data_type: uint16
        unit_of_measurement: "ppm"
        device_class: carbon_dioxide
        state_class: measurement

      # System power
      - name: "HRUC System Power"
        address: 30010
        slave: 2
        data_type: uint16
        unit_of_measurement: "W"
        device_class: power
        state_class: measurement

      # Filter timer
      - name: "HRUC Filter Timer"
        address: 30003
        slave: 2
        data_type: uint16
        unit_of_measurement: "months"

      # Service timer
      - name: "HRUC Service Timer"
        address: 30002
        slave: 2
        data_type: uint16
        unit_of_measurement: "months"

      # Run time
      - name: "HRUC Run Time"
        address: 30001
        slave: 2
        data_type: uint16
        unit_of_measurement: "days"

    # Control via holding register 40030
    # This will require custom number/select entity
    # Example implementation in separate package
```

## Implementation Plan

1. **Phase 1: Hardware Setup**
   - Purchase RS485 to USB adapter
   - Open unit and locate RS485 terminals
   - Connect adapter (A, B, GND)
   - Route USB cable to Home Assistant server

2. **Phase 2: Basic Configuration**
   - Configure Modbus serial interface in HA
   - Test basic register reads (30001 - run time)
   - Verify communication is working

3. **Phase 3: Sensor Setup**
   - Add all temperature sensors
   - Add humidity sensors
   - Add CO2 sensors
   - Add status sensors (filter, service, power)

4. **Phase 4: Control Setup**
   - Test writing to register 40030
   - Map preset values to ventilation modes
   - Create select/number entities for mode control
   - Test mode changes

5. **Phase 5: Advanced Features**
   - Add fault/warning monitoring (bitmask decoding)
   - Create binary sensors for output status
   - Add zone sensors if applicable
   - Create dashboard cards

## Questions for Robbert

Before proceeding, you may want to ask:

1. **RS485 Terminal Location:** Where exactly are the RS485 A/B terminals on the circuit board?
2. **Warranty:** Does opening the unit void the warranty?
3. **Register 40030 Values:** What are the exact preset values for each ventilation mode (Auto, Low, Med, High, Boost)?
4. **Virtual Inputs:** What do registers 40001-40010 control?
5. **Configuration:** How to set Modbus address and baud rate via app?
6. **Wiring Diagram:** Is there a diagram showing RS485 connection points?

## Conclusion

The Modbus approach is **technically superior** to PSK extraction:
- ✅ Standard protocol with native HA support
- ✅ Complete sensor and control access
- ✅ No reverse engineering required
- ✅ Reliable wired connection
- ❌ Requires hardware purchase (~€25)
- ❌ Requires physical installation

**Recommendation:** Proceed with Modbus integration if you're comfortable with physical installation. This is a cleaner, more maintainable long-term solution compared to the proprietary TLS-PSK protocol.
