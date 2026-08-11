#!/usr/bin/env python3
"""
ComAir HRUC-Plus / Vent-Axia Sentinel Kinetic - Modbus gateway diagnostic.

Tests the RS485-to-WiFi/Ethernet gateway (Elfin EW11A or similar) that sits
between Home Assistant and the MVHR unit's BMS port, and reports which side of
the chain is broken.

Requires only Python 3 - no pymodbus, no Home Assistant. Run it from any machine
on the same network, or from the "Advanced SSH & Web Terminal" add-on.

    python3 gateway_test.py <gateway_ip> [port]
    python3 gateway_test.py 192.168.1.50
    python3 gateway_test.py 192.168.1.50 502
"""

import socket
import struct
import sys

TIMEOUT = 3.0

# Input register 0 == register 30001 "Run Time" in the Vent-Axia BMS map.
# Every unit implements it, so it is the safest register to ask for.
FUNC = 4
ADDR = 0
COUNT = 1


def crc16(data: bytes) -> bytes:
    """Modbus RTU CRC-16, little endian."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return struct.pack("<H", crc)


def rtu_frame(device_id: int) -> bytes:
    """Modbus RTU framing: raw PDU plus CRC, no header."""
    frame = bytearray([device_id, FUNC]) + struct.pack(">HH", ADDR, COUNT)
    return bytes(frame + crc16(frame))


def mbap_frame(device_id: int) -> bytes:
    """Modbus TCP framing: 7-byte MBAP header, no CRC."""
    pdu = bytes([device_id, FUNC]) + struct.pack(">HH", ADDR, COUNT)
    return struct.pack(">HHH", 1, 0, len(pdu)) + pdu


def send_raw(host: str, port: int, payload: bytes) -> bytes:
    """Open a fresh TCP connection, send payload, return whatever comes back."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(TIMEOUT)
    try:
        sock.connect((host, port))
        sock.sendall(payload)
        return sock.recv(512)
    finally:
        sock.close()


def hx(data: bytes) -> str:
    return data.hex(" ") if data else "(nothing)"


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2

    host = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 502

    print("=" * 62)
    print(f" ComAir / Vent-Axia gateway test -> {host}:{port}")
    print("=" * 62)

    # ------------------------------------------------------------- TEST 1
    print("\n[1] TCP connection to the gateway")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT)
        sock.connect((host, port))
        sock.close()
        print("    OK - gateway is reachable and the port is open")
    except OSError as err:
        print(f"    FAILED: {err}")
        print("\n    STOP: wrong IP/port, or the gateway is not in TCP Server mode.")
        return 1

    # ------------------------------------------------------------- TEST 2
    print("\n[2] Modbus RTU over TCP, device ID 2  <- what the integration uses")
    sent = rtu_frame(2)
    print(f"    sent: {hx(sent)}")
    rtu_ok = False
    rtu_reply = b""
    try:
        rtu_reply = send_raw(host, port, sent)
        print(f"    recv: {hx(rtu_reply)}  ({len(rtu_reply)} bytes)")
        if len(rtu_reply) >= 5 and rtu_reply[0] == 2 and rtu_reply[1] == FUNC:
            value = struct.unpack(">h", rtu_reply[3:5])[0]
            print(f"    OK - valid Modbus RTU reply, register value = {value}")
            rtu_ok = True
        elif len(rtu_reply) >= 3 and rtu_reply[0] == 2 and rtu_reply[1] == FUNC + 0x80:
            print(f"    Unit ANSWERED with Modbus exception code {rtu_reply[2]}")
            print("    -> communication works, only the register was refused")
            rtu_ok = True
        else:
            print("    GARBAGE - bytes came back but they are not a Modbus reply")
    except socket.timeout:
        print("    recv: (nothing - timeout)")
    except OSError as err:
        print(f"    ERROR: {err}")

    # ------------------------------------------------------------- TEST 3
    print("\n[3] Modbus TCP framing, device ID 2  <- detects wrong gateway mode")
    sent = mbap_frame(2)
    print(f"    sent: {hx(sent)}")
    mbap_ok = False
    try:
        reply = send_raw(host, port, sent)
        print(f"    recv: {hx(reply)}  ({len(reply)} bytes)")
        if len(reply) >= 9 and reply[7] == 2 and reply[8] == FUNC:
            print("    Gateway replied in Modbus TCP -> it is in Modbus conversion")
            print("    mode, not transparent mode")
            mbap_ok = True
        else:
            print("    no valid Modbus TCP reply (expected, if the mode is correct)")
    except socket.timeout:
        print("    recv: (nothing - timeout)")
    except OSError as err:
        print(f"    ERROR: {err}")

    # ------------------------------------------------------------- TEST 4
    print("\n[4] Scanning device IDs 1-16 (RTU over TCP)")
    found = []
    for device_id in range(1, 17):
        try:
            reply = send_raw(host, port, rtu_frame(device_id))
        except OSError:
            reply = b""
        if len(reply) >= 3 and reply[0] == device_id and reply[1] in (FUNC, FUNC + 0x80):
            print(f"    ID {device_id:>3}: ANSWERED  {hx(reply)}")
            found.append(device_id)
        elif reply:
            print(f"    ID {device_id:>3}: {len(reply)} bytes, not valid: {hx(reply[:12])}")
        else:
            print(f"    ID {device_id:>3}: silent")
    print("\n    Note: if Home Assistant is polling the same gateway while this runs,")
    print("    unrelated IDs can show stray bytes. That is the two clients sharing")
    print("    one gateway, not a fault.")

    # ------------------------------------------------------------- VERDICT
    print("\n" + "=" * 62)
    print(" VERDICT")
    print("=" * 62)

    if rtu_ok or found:
        ids = ", ".join(str(i) for i in found) or "2"
        print(f" Modbus works. Device ID(s) that answered: {ids}")
        print(" -> Use that ID in the integration. If Home Assistant still fails,")
        print("    the gateway accepts only a few TCP clients - restart HA.")
    elif mbap_ok:
        print(" The GATEWAY answers but the UNIT does not, and the gateway is in")
        print(" Modbus conversion mode. Fix its serial settings:")
        print("     Serial / UART  ->  Protocol = None   (NOT 'Modbus')")
        print(" On an Elfin EW11A this is the Protocol dropdown on the Serial")
        print(" Settings page. Save, wait ~10 s for the restart, test again.")
    elif not rtu_reply:
        print(" Nothing comes back from the serial side at all. Two options:")
        print("   a) the gateway never puts the request on the RS485 wire")
        print("      -> Serial Settings: Protocol = None")
        print("      -> Communication Settings: Protocol = Tcp Server,")
        print("         Local Port = 502, Route = Uart")
        print("   b) the request goes out but the unit does not answer")
        print("      -> watch the serial Tx/Rx counters on the gateway status page")
        print("      -> wrong connector (must be the BMS RJ12, not the '+ A B -'")
        print("         sensor connectors), A/B swapped, missing GND, or wrong baud")
    else:
        print(" Bytes come back but they are not Modbus -> almost always a baud")
        print(" rate mismatch, or the wires are on the wrong connector. Confirm")
        print(" 115200 / 8 / None / 1 on both the gateway and in the app.")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
