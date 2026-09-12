#!/usr/bin/env python3
"""
deploy.py — Deploy qStack dev cluster (Talos Linux on VirtualBox).

Talos is designed for multi-node clusters. This script always deploys:
  1 Control Plane VM  +  1 Worker VM

For single-node dev, use k3s: scripts/deploy-k3s.py

Usage:
  python deploy.py --up      # Deploy 1 CP + 1 Worker (2 VMs, 8GB RAM total)
  python deploy.py --down    # Destroy cluster
  python deploy.py --status  # Check status
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

# ── Config ────────────────────────────────────────────────────────────────────

TALOS_VERSION = "v1.6.2"
SCHEMATIC_ID = "376567988ad370138ad8b2698212367b8edcb69b5fd68c80be1f2ec7d603b4ba"

# Node names and IPs
CP_NAME = f"{CLUSTER_NAME}-cp-00"
CP_IP = f"{BASE_IP}.10"


# ── Helpers ──────────────────────────────────────────────────────────────────

def find_exe(name: str, search_dirs: Optional[list[str]] = None) -> str:
    """Find executable in PATH or common Windows dirs."""
    cmd = shutil.which(name)
    if cmd:
        return cmd

    dirs = search_dirs or [
        r"C:\ProgramData\chocolatey\bin",
        r"C:\Program Files\Oracle\VirtualBox",
        r"C:\Program Files (x86)\Oracle\VirtualBox",
    ]
    for d in dirs:
        if os.path.isdir(d):
            for ext in ["", ".exe", ".cmd", ".bat"]:
                candidate = os.path.join(d, name + ext)
                if os.path.isfile(candidate):
                    return candidate
    return name


def run(cmd: list[str], check: bool = True, timeout: int = 60) -> str:
    """Run command, return combined stdout+stderr."""
    return out


def print_step(n: int, msg: str):
    print(f"\n[{n}] {msg}")


def print_info(msg: str):
    print(f"  ℹ {msg}")




def start_vm(name: str):
    """Start VM headless."""
    run([find_exe("VBoxManage"), "startvm", name, "--type", "headless"])


def poweroff_vm(name: str):
    """Power off VM."""
    run([find_exe("VBoxManage"), "controlvm", name, "poweroff"], check=False)


def remove_vm(name: str):
    """Unregister and delete VM."""
    run([find_exe("VBoxManage"), "unregistervm", name, "--delete"], check=False)


# ── Talos ────────────────────────────────────────────────────────────────────

def download_iso() -> str:
    """Download Talos ISO if not present."""
    iso_path = Path(ISO_NAME)
    start = time.time()
    while time.time() - start < timeout:
        r = subprocess.run(
            [find_exe("talosctl"), "ping", "--nodes", ip],
            capture_output=True, text=True, timeout=10,
        )
        combined = (r.stdout + r.stderr).lower()
    return False


def gen_config():
    """Generate Talos cluster config."""
    print_info("Generating Talos config...")
    cmd = [


def apply_config(ip: str, role: str):
    """Apply machine config to node."""
    print_info(f"Applying {role} config to {ip}...")


def bootstrap(ip: str):
    """Bootstrap the control plane."""
    print_info("Bootstrapping control plane...")


def get_kubeconfig(ip: str):
    """Export kubeconfig to ~/.kube/config."""


def verify_cluster():
    """Show cluster status."""
    print_info("Cluster nodes:")
    print(f"  {out}")


# ── Commands ─────────────────────────────────────────────────────────────────

def cmd_up(_args: argparse.Namespace):
    print_step(1, "Download Talos ISO")

    print_step(4, "Start VMs")
    start_vm(CP_NAME)
    start_vm(WK_NAME)


    print_step(6, "Generate Talos Config")
    gen_config()

    print_step(7, "Apply Config")
    apply_config(CP_IP, "controlplane")
    apply_config(WK_IP, "worker")

    print_step(8, "Bootstrap Cluster")
    bootstrap(CP_IP)

    print_step(9, "Get Kubeconfig")
    get_kubeconfig(CP_IP)

    print_step(10, "Verify Cluster")
    verify_cluster()

    print(f"   kubectl get nodes")
    print(f"   kubectl apply -f k8s/")


def cmd_down(_args: argparse.Namespace):
    print_info("Shutting down cluster...")
    for name in [CP_NAME, WK_NAME]:
    run([find_exe("VBoxManage"), "list", "runningvms"], check=False)

    print_info("\nTalos nodes:")
    run([find_exe("talosctl"), "get", "nodes"], check=False)

    print_info("\nK8s nodes:")
    run([find_exe("kubectl"), "get", "nodes"], check=False)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser.add_argument("--up", action="store_true", help="Deploy 1 CP + 1 Worker cluster")
    parser.add_argument("--down", action="store_true", help="Destroy cluster")
    parser.add_argument("--status", action="store_true", help="Show status")
    args = parser.parse_args()

    if args.up:
        cmd_up(args)
    elif args.down:
        cmd_down(args)
    elif args.status:
        cmd_status(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
