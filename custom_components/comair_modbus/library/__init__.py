"""Vendored device library for the ComAir HRUC-Plus MVHR.

A thin layer over ``modbus-connection`` that owns the register map and the
device semantics. It deliberately imports nothing from Home Assistant, so
the protocol half can be exercised on its own.
"""
from __future__ import annotations

from .components import (
    Airflow,
    Fans,
    Outputs,
    Settings,
    Status,
    VirtualInputs,
    Zone,
)
from .device import ComairHruC

__all__ = [
    "Airflow",
    "ComairHruC",
    "Fans",
    "Outputs",
    "Settings",
    "Status",
    "VirtualInputs",
    "Zone",
]