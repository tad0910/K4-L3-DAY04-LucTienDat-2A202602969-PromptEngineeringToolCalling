from __future__ import annotations

from datetime import datetime
from typing import Any

from tools._shared import err


NETWORK_TARGETS = {
    "vpn": {"ip": "10.10.1.1", "port": 443, "base_latency": 25, "status": "healthy"},
    "email": {"ip": "10.10.2.25", "port": 587, "base_latency": 15, "status": "healthy"},
    "sso": {"ip": "10.10.3.10", "port": 443, "base_latency": 12, "status": "healthy"},
    "dns": {"ip": "10.10.0.2", "port": 53, "base_latency": 4, "status": "healthy"},
    "gateway": {"ip": "10.10.0.1", "port": 80, "base_latency": 2, "status": "healthy"},
    "internet": {"ip": "8.8.8.8", "port": 53, "base_latency": 30, "status": "healthy"},
}


def diagnose_network(target: str = "vpn", test_type: str = "ping") -> dict[str, Any]:
    """Simulated network diagnostics tool for testing connectivity, ping, and DNS resolution."""
    try:
        target_key = (target or "vpn").strip().lower()
        test_key = (test_type or "ping").strip().lower()

        info = NETWORK_TARGETS.get(target_key, {"ip": "10.10.99.99", "port": 80, "base_latency": 45, "status": "reachable"})
        now_str = datetime.now().isoformat(timespec="seconds")

        if test_key == "dns_lookup":
            return {
                "tool": "diagnose_network",
                "target": target_key,
                "test_type": "dns_lookup",
                "resolved_ip": info["ip"],
                "status": "resolved",
                "dns_server": "10.10.0.2",
                "tested_at": now_str,
            }
        elif test_key == "port_check":
            return {
                "tool": "diagnose_network",
                "target": target_key,
                "test_type": "port_check",
                "target_ip": info["ip"],
                "port": info["port"],
                "port_status": "open",
                "tested_at": now_str,
            }
        else:  # ping or traceroute
            return {
                "tool": "diagnose_network",
                "target": target_key,
                "test_type": test_key,
                "target_ip": info["ip"],
                "latency_ms": info["base_latency"],
                "packet_loss_pct": 0,
                "status": info["status"],
                "summary": f"Ping to {target_key} ({info['ip']}) successful: 0% loss, latency {info['base_latency']}ms",
                "tested_at": now_str,
            }
    except Exception as exc:
        return err("diagnose_network", exc)
