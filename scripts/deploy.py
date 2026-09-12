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
NETWORK = "192.168.56.0/24"
BASE_IP = "192.168.56"
CLUSTER_NAME = "qStack"

# VM specs (2 × 4GB = 8GB total — enough for dev)
VM_CPU = 2
VM_DISK = 20480  # 20GB per VM

ISO_NAME = f"talos-{TALOS_VERSION}-metal-amd64.iso"
ISO_URL = f"https://factory.talos.dev/image/{SCHEMATIC_ID}/{TALOS_VERSION}/metal-amd64.iso"

# Node names and IPs
CP_NAME = f"{CLUSTER_NAME}-cp-00"
CP_IP = f"{BASE_IP}.10"
CP_RAM = 4096

WK_NAME = f"{CLUSTER_NAME}-wk-00"
WK_IP = f"{BASE_IP}.20"
WK_RAM = 4096


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
    print(f"  > {cmd[0]} {' '.join(cmd[1:4])}...")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    out = (r.stdout + r.stderr).strip()
    if check and r.returncode != 0 and "not found" in out:
        print(f"  ✗ Command not found: {cmd[0]}")
        sys.exit(1)
    return out


def print_step(n: int, msg: str):
    print(f"\n[{n}] {msg}")


def print_info(msg: str):
    print(f"  ℹ {msg}")


# ── VirtualBox ───────────────────────────────────────────────────────────────

def setup_network():
    """Create NAT network for VMs."""
    print_info("Setting up NAT network...")
    run([find_exe("VBoxManage"), "natnetwork", "remove", "--netname", "natnet0"], check=False)
    run([find_exe("VBoxManage"), "natnetwork", "add", "--netname", "natnet0",
         "--network", NETWORK, "--ipv6", "off", "--autoconfig", "off"])


def create_vm(name: str, ip: str, ram: int, iso_path: str):
    """Create a VirtualBox VM with Talos ISO."""
    vdi = f"{name}.vdi"

    print_info(f"Creating VM: {name} (RAM {ram}MB, CPU {VM_CPU}, {VM_DISK // 1024}GB disk)")
    run([find_exe("VBoxManage"), "createvm", "--name", name, "--register"])
    run([find_exe("VBoxManage"), "modifyvm", name, "--memory", str(ram), "--cpus", str(VM_CPU), "--ioapic", "on"])
    run([find_exe("VBoxManage"), "modifyvm", name, "--nic1", "natnetwork"])
    run([find_exe("VBoxManage"), "modifyvm", name, "--nat-network1", "natnet0"])
    run([find_exe("VBoxManage"), "modifyvm", name, "--nat-localhostproxy1", "on"])
    run([find_exe("VBoxManage"), "modifyvm", name, "--nicpromisc1", "deny"])

    # Storage controller + HDD
    run([find_exe("VBoxManage"), "storagectl", name, "--name", "SATA", "--add", "sata"])
    if not Path(vdi).exists():
        run([find_exe("VBoxManage"), "createhd", "--filename", vdi, "--size", str(VM_DISK)])
    run([find_exe("VBoxManage"), "storageattach", name, "--storagectl", "SATA",
         "--port", "0", "--device", "0", "--type", "hdd", "--medium", vdi])
    # ISO (boot/install)
    run([find_exe("VBoxManage"), "storageattach", name, "--storagectl", "SATA",
         "--port", "1", "--device", "0", "--type", "dvddrive", "--medium", iso_path])


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
    if iso_path.exists():
        print_info(f"ISO already exists: {ISO_NAME}")
        return str(iso_path)

    print_info(f"Downloading Talos ISO (~{200}MB)...")
    downloader = shutil.which("aria2c") or shutil.which("curl")
    if not downloader:
        print("  ✗ curl or aria2c not found")
        sys.exit(1)

    if "aria2c" in downloader:
        run([downloader, "-s4", "-x4", "-o", ISO_NAME, ISO_URL], check=False)
    else:
        run([downloader, "-L", "-o", ISO_NAME, ISO_URL], check=False)

    if not iso_path.exists():
        print("  ✗ ISO download failed")
        sys.exit(1)
    print_info(f"ISO downloaded: {ISO_NAME}")
    return str(iso_path)


def wait_for_boot(name: str, ip: str, timeout: int = 300) -> bool:
    """Wait for Talos API (port 50000) to be ready."""
    print_info(f"Waiting for {name} to boot ({ip}:50000)...")
    start = time.time()
    while time.time() - start < timeout:
        r = subprocess.run(
            [find_exe("talosctl"), "ping", "--nodes", ip],
            capture_output=True, text=True, timeout=10,
        )
        combined = (r.stdout + r.stderr).lower()
        if "ok" in combined or "success" in combined:
            print_info(f"✓ {name} is ready!")
            return True
        time.sleep(5)
    print(f"  ⚠ Timed out waiting for {name} ({timeout}s). Proceeding anyway.")
    return False


def gen_config():
    """Generate Talos cluster config."""
    print_info("Generating Talos config...")
    cmd = [
        find_exe("talosctl"), "gen", "config", CLUSTER_NAME, f"{CP_IP}:6443",
        "--output", "talos-cluster",
        "--install-image", f"factory.talos.dev/metal-installer/{SCHEMATIC_ID}:{TALOS_VERSION}",
        "--worker-endpoint", WK_IP,
    ]
    run(cmd)


def apply_config(ip: str, role: str):
    """Apply machine config to node."""
    print_info(f"Applying {role} config to {ip}...")
    run([
        find_exe("talosctl"), "apply-config",
        "--file", f"talos-cluster/machines/{role}.yaml",
        "--nodes", ip,
    ])


def bootstrap(ip: str):
    """Bootstrap the control plane."""
    print_info("Bootstrapping control plane...")
    run([find_exe("talosctl"), "bootstrap", "--nodes", ip])


def get_kubeconfig(ip: str):
    """Export kubeconfig to ~/.kube/config."""
    print_info("Exporting kubeconfig...")
    run([find_exe("talosctl"), "kubeconfig", "--nodes", ip, os.path.expanduser("~/.kube/config")])
    print_info("✓ kubeconfig → ~/.kube/config")


def verify_cluster():
    """Show cluster status."""
    print_info("Cluster nodes:")
    out = run([find_exe("kubectl"), "get", "nodes", "-o", "wide"])
    print(f"  {out}")


# ── Commands ─────────────────────────────────────────────────────────────────

def cmd_up(_args: argparse.Namespace):
    print_step(1, "Download Talos ISO")
    iso_path = download_iso()

    print_step(2, "Setup Network")
    setup_network()

    print_step(3, "Create VMs")
    create_vm(CP_NAME, CP_IP, CP_RAM, iso_path)
    create_vm(WK_NAME, WK_IP, WK_RAM, iso_path)

    print_step(4, "Start VMs")
    start_vm(CP_NAME)
    start_vm(WK_NAME)

    print_step(5, "Wait for boot")
    wait_for_boot(CP_NAME, CP_IP)
    wait_for_boot(WK_NAME, WK_IP)

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

    print("\n✅ Cluster ready! Deploy qStack:")
    print(f"   kubectl get nodes")
    print(f"   kubectl apply -f k8s/")


def cmd_down(_args: argparse.Namespace):
    print_info("Shutting down cluster...")
    for name in [CP_NAME, WK_NAME]:
        print_info(f"Powering off {name}...")
        poweroff_vm(name)
        time.sleep(2)

    for name in [CP_NAME, WK_NAME]:
        print_info(f"Removing {name}...")
        remove_vm(name)

    run([find_exe("VBoxManage"), "natnetwork", "remove", "--netname", "natnet0"], check=False)
    print("✅ Cluster destroyed.")


def cmd_status(_args: argparse.Namespace):
    print_info("Running VMs:")
    run([find_exe("VBoxManage"), "list", "runningvms"], check=False)

    print_info("\nTalos nodes:")
    run([find_exe("talosctl"), "get", "nodes"], check=False)

    print_info("\nK8s nodes:")
    run([find_exe("kubectl"), "get", "nodes"], check=False)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Deploy qStack dev cluster (Talos + VirtualBox)")
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
