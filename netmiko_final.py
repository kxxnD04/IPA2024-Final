from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

from netmiko import ConnectHandler
from netmiko.exceptions import (
    NetmikoAuthenticationException,
    NetmikoTimeoutException,
)

ROUTER_IP = "10.0.15.61"
USERNAME = "admin"
PASSWORD = "cisco"

TARGET_INTERFACES = [
    "GigabitEthernet1",
    "GigabitEthernet2",
    "GigabitEthernet3",
    "GigabitEthernet4",
]


@dataclass
class InterfaceStatus:
    name: str
    admin_status: str


def _collect_interfaces(result: Iterable[Dict[str, str]]) -> List[InterfaceStatus]:
    interfaces: List[InterfaceStatus] = []
    for entry in result:
        name = entry.get("intf") or entry.get("interface") or ""
        if name not in TARGET_INTERFACES:
            continue
        status = entry.get("status", "").strip().lower()
        if not status:
            continue
        interfaces.append(InterfaceStatus(name=name, admin_status=status))
    return interfaces


def gigabit_status() -> str:
    device_params = {
        "device_type": "cisco_xe",
        "ip": ROUTER_IP,
        "username": USERNAME,
        "password": PASSWORD,
        "conn_timeout": 25,
        "banner_timeout": 120,
        "auth_timeout": 25,
        "global_delay_factor": 2,
        "fast_cli": False,
    }

    try:
        with ConnectHandler(**device_params) as ssh:  # type: ignore[arg-type]
            result = ssh.send_command(
                "show ip interface brief",
                use_textfsm=True,
                delay_factor=2,
            )

            if not isinstance(result, list):
                raw_output = ssh.send_command(
                    "show ip interface brief",
                    delay_factor=2,
                )
                result = _parse_raw_show_ip_interface_brief(raw_output)
    except (NetmikoTimeoutException, NetmikoAuthenticationException) as exc:
        print(f"Netmiko connection error: {exc}")
        return "Error: Netmiko"

    if not isinstance(result, list):
        return "Error: Netmiko"

    interfaces = _collect_interfaces(result)
    if not interfaces:
        return "Error: Netmiko"

    # Ensure the response follows the expected ordering no matter how CLI returns data
    interface_lookup: Dict[str, InterfaceStatus] = {item.name: item for item in interfaces}

    ordered_interfaces: List[InterfaceStatus] = []
    for name in TARGET_INTERFACES:
        entry = interface_lookup.get(name)
        if entry is not None:
            ordered_interfaces.append(entry)

    if not ordered_interfaces:
        return "Error: Netmiko"

    up_count = sum(1 for intf in ordered_interfaces if intf.admin_status == "up")
    down_count = sum(1 for intf in ordered_interfaces if intf.admin_status == "down")
    admin_down_count = sum(
        1 for intf in ordered_interfaces if intf.admin_status == "administratively down"
    )

    statuses = [f"{intf.name} {intf.admin_status}" for intf in ordered_interfaces]
    if not statuses:
        return "Error: Netmiko"

    status_text = ", ".join(statuses)
    summary = (
        f"{status_text} -> {up_count} up, {down_count} down, {admin_down_count} administratively down"
    )
    return summary


def _parse_raw_show_ip_interface_brief(output: str) -> List[Dict[str, str]]:
    lines = output.splitlines()
    entries: List[Dict[str, str]] = []
    header_found = False
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.lower().startswith("interface"):
            header_found = True
            continue
        if not header_found:
            continue
        parts = line.split()
        if len(parts) < 6:
            continue
        name = parts[0]
        if name not in TARGET_INTERFACES:
            continue
        status = " ".join(parts[4:-1]).strip().lower()
        if not status:
            status = parts[4].lower()
        entries.append({"intf": name, "status": status})
    return entries
