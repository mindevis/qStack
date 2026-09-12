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

# Host-only network (host ↔ VM direct connectivity)
HOSTONLY_NET = "vboxnet0"
NETWORK_CIDR = "192.168.56.0/24"
BASE_IP = "192.168.56"
CLUSTER_NAME = "qStack"

# VM specs
VM_CPU = 2
VM_DISK = 20480  # 20GB per VM
CP_RAM = 4096
WK_RAM = 4096

# Node names and IPs
CP_NAME = f"{CLUSTER_NAME}-cp-00"
CP_IP = f"{BASE_IP}.10"
WK_NAME = f"{CLUSTER_NAME}-wk-00"
WK_IP = f"{BASE_IP}.20"

# Talos ISO from GitHub releases (direct download)
ISO_NAME = f"metal-amd64.iso"
ISO_URL = f"https://github.com/siderolabs/talos/releases/download/{TALOS_VERSION}/metal-amd64.iso"


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
    short = cmd[0] + " " + " ".join(cmd[1:min(4, len(cmd))])
    print(f"  > {short}...")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    out = (r.stdout + r.stderr).strip()
    if check and r.returncode != 0:
        if "not found" in out.lower():
            print(f"  ✗ Command not found: {cmd[0]}")
            sys.exit(1)
        # Don't fail on non-zero if check=False
        if check:
            print(f"  ⚠ Non-zero exit: {r.returncode}")
    return out


def print_step(n: int, msg: str):
    print(f"\n[{n}] {msg}")


def print_info(msg: str):
    print(f"  ℹ {msg}")


def print_ok(msg: str):
    print(f"  ✓ {msg}")


# ── VirtualBox ───────────────────────────────────────────────────────────────

def ensure_hostonly_net():
    """Ensure host-only network vboxnet0 exists."""
    # Check if it already exists
    out = run(
        [find_exe("VBoxManage"), "hostonlyif", "list"],
        check=False, timeout=10,
    )
    if HOSTONLY_NET in out:
        print_info(f"Host-only network {HOSTONLY_NET} already exists")
        return

    # Create it
    print_info(f"Creating host-only network {HOSTONLY_NET}...")
    run([find_exe("VBoxManage"), "hostonlyif", "create"])

    # Configure the interface (find which one was created)
    out = run([find_exe("VBoxManage"), "hostonlyif", "list"], check=False)
    # The newly created interface should be in the output
    # On Windows, it might be named vboxnet0, vboxnet1, etc.
    interfaces = [line.strip() for line in out.split("\n") if "Name:" in line]
    new_iface = interfaces[-1].split(":")[-1].strip() if interfaces else HOSTONLY_NET

    print_info(f"Configuring {new_iface} with {NETWORK_CIDR}...")
    # Remove existing IP config and set new one
    run([find_exe("VBoxManage"), "hostonlyif", "ipconfig", new_iface,
         "--ip", BASE_IP + ".1", "--netmask", "255.255.255.0"], check=False)


def create_vm(name: str, ram: int):
    """Create a VirtualBox VM."""
    vdi = f"{name}.vdi"

    print_info(f"Creating VM: {name} (RAM {ram}MB, CPU {VM_CPU}, {VM_DISK // 1024}GB disk)")

    if Path(f"{name}.vbox").exists() or _vm_exists(name):
        print_info(f"VM {name} already exists, reusing")
        return

    run([find_exe("VBoxManage"), "createvm", "--name", name, "--register"])

    # Basic config
    run([find_exe("VBoxManage"), "modifyvm", name,
         "--memory", str(ram), "--cpus", str(VM_CPU),
         "--ioapic", "on", "--pae", "on", "--acpi", "on"])

    # Network: host-only
    run([find_exe("VBoxManage"), "modifyvm", name,
         "--nic1", "hostonly", "--hostonlyadapter1", HOSTONLY_NET])

    # Storage controller + HDD
    run([find_exe("VBoxManage"), "storagectl", name, "--name", "SATA", "--add", "sata"])

    if not Path(vdi).exists():
        run([find_exe("VBoxManage"), "createhd", "--filename", vdi,
             "--size", str(VM_DISK), "--variant", "Fixed"])
    run([find_exe("VBoxManage"), "storageattach", name, "--storagectl", "SATA",
         "--port", "0", "--device", "0", "--type", "hdd", "--medium", vdi])

    # ISO (boot/install)
    iso_path = Path(ISO_NAME)
    if iso_path.exists():
        run([find_exe("VBoxManage"), "storageattach", name, "--storagectl", "SATA",
             "--port", "1", "--device", "0", "--type", "dvddrive", "--medium", str(iso_path)])

    # Boot order: DVD first (for installation), then disk
    run([find_exe("VBoxManage"), "modifyvm", name,
         "--boot1", "dvd", "--boot2", "disk", "--bootmenu", "disabled"])


def _vm_exists(name: str) -> bool:
    out = run([find_exe("VBoxManage"), "list", "vms"], check=False)
    return name in out


def start_vm(name: str):
    """Start VM headless."""
    run([find_exe("VBoxManage"), "startvm", name, "--type", "headless"])
    time.sleep(1)  # Give VM time to start


def is_vm_running(name: str) -> bool:
    out = run([find_exe("VBoxManage"), "showvminfo", name, "--machinereadable"], check=False)
    return 'VMState="running"' in out


def poweroff_vm(name: str):
    """Power off VM."""
    run([find_exe("VBoxManage"), "controlvm", name, "poweroff"], check=False)
    for _ in range(30):
        if not is_vm_running(name):
            return
        time.sleep(1)


def remove_vm(name: str):
    """Unregister and delete VM."""
    run([find_exe("VBoxManage"), "unregistervm", name, "--delete"], check=False)


# ── Talos ────────────────────────────────────────────────────────────────────

def download_iso() -> str:
    """Download Talos ISO if not present."""
    iso_path = Path(ISO_NAME)
    if iso_path.exists() and iso_path.stat().st_size > 10_000_000:  # >10MB
        print_info(f"ISO already exists: {ISO_NAME} ({iso_path.stat().st_size // 1024 // 1024}MB)")
        return str(iso_path)

    print_info(f"Downloading Talos ISO (~200MB)...")
    downloader = shutil.which("curl")
    if not downloader:
        print("  ✗ curl not found")
        sys.exit(1)

    run([downloader, "-f", "-L", "-o", ISO_NAME, ISO_URL], check=False)

    if not iso_path.exists() or iso_path.stat().st_size < 10_000_000:
        print(f"  ✗ ISO download failed or too small")
        print(f"  ℹ URL: {ISO_URL}")
        sys.exit(1)
    print_ok(f"ISO downloaded: {ISO_NAME} ({iso_path.stat().st_size // 1024 // 1024}MB)")
    return str(iso_path)


def wait_for_talos(ip: str, timeout: int = 300) -> bool:
    """Wait for Talos API (port 50000) to respond."""
    print_info(f"Waiting for Talos API on {ip}:50000...")
    start = time.time()
    while time.time() - start < timeout:
        r = subprocess.run(
            [find_exe("talosctl"), "ping", "--nodes", ip],
            capture_output=True, text=True, timeout=10,
        )
        combined = (r.stdout + r.stderr).lower()
        if "ok" in combined or "success" in combined or "alive" in combined:
            return True
        time.sleep(5)
    print(f"  ⚠ Timed out waiting for {ip} ({timeout}s)")
    return False


def gen_config():
    """Generate Talos cluster config."""
    print_info("Generating Talos config...")
    cmd = [
        find_exe("talosctl"), "gen", "config", CLUSTER_NAME,
        f"https://{CP_IP}:6443",
        "--output", "talos-cluster",
        "--worker", f"{WK_IP}",
    ]
    out = run(cmd, timeout=30)
    if "generated" in out.lower() or "created" in out.lower():
        print_ok("Config generated")
    else:
        print(f"  ⚠ Output: {out[:200]}")


def apply_config(ip: str, role: str):
    """Apply machine config to node."""
    print_info(f"Applying {role} config to {ip}...")
    role_file = f"talos-cluster/machines/{role}.yaml"
    if not Path(role_file).exists():
        # Try alternative naming
        if role == "controlplane":
            role_file = "talos-cluster/machines/controlplane.yaml"
        elif role == "worker":
            role_file = "talos-cluster/machines/worker.yaml"

    run([
        find_exe("talosctl"), "apply-config",
        "--file", role_file,
        "--nodes", ip,
    ], timeout=60)
    print_ok(f"{role} config applied to {ip}")


def bootstrap(ip: str):
    """Bootstrap the control plane."""
    print_info("Bootstrapping control plane...")
    run([find_exe("talosctl"), "bootstrap", "--nodes", ip], timeout=60)
    print_ok("Control plane bootstrapped")


def get_kubeconfig(ip: str):
    """Export kubeconfig to ~/.kube/config."""
    kube_dir = Path.home() / ".kube"
    kube_dir.mkdir(exist_ok=True)
    kubeconfig = str(kube_dir / "config")
    print_info(f"Exporting kubeconfig → {kubeconfig}...")
    run([find_exe("talosctl"), "kubeconfig", "--nodes", ip, kubeconfig], timeout=30)
    print_ok(f"kubeconfig → {kubeconfig}")


def verify_cluster():
    """Show cluster status."""
    print_info("Cluster nodes:")
    out = run([find_exe("kubectl"), "get", "nodes", "-o", "wide"], timeout=30)
    print(f"  {out}")


# ── Commands ─────────────────────────────────────────────────────────────────

def cmd_up(_args: argparse.Namespace):
    print_step(1, "Download Talos ISO")
    download_iso()

    print_step(2, "Setup Host-Only Network")
    ensure_hostonly_net()

    print_step(3, "Create VMs")
    create_vm(CP_NAME, CP_RAM)
    create_vm(WK_NAME, WK_RAM)

    print_step(4, "Start VMs")
    start_vm(CP_NAME)
    start_vm(WK_NAME)

    # Verify VMs are actually running
    time.sleep(3)
    for name in [CP_NAME, WK_NAME]:
        if is_vm_running(name):
            print_ok(f"{name} is running")
        else:
            print(f"  ✗ {name} failed to start!")
            print_info("Check VirtualBox for errors")
            sys.exit(1)

    print_step(5, "Wait for Talos boot")
    cp_ready = wait_for_talos(CP_IP)
    wk_ready = wait_for_talos(WK_IP)

    if not cp_ready:
        print("  ✗ Control plane did not boot in time. Check VM logs in VirtualBox.")
        sys.exit(1)
    print_ok("Talos cluster booted")

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

    print("\n✅ Cluster ready!")
    print(f"   kubectl get nodes")
    print(f"   kubectl apply -f k8s/")


def cmd_down(_args: argparse.Namespace):
    print_info("Shutting down cluster...")
    for name in [CP_NAME, WK_NAME]:
        if _vm_exists(name):
            print_info(f"Powering off {name}...")
            poweroff_vm(name)

    for name in [CP_NAME, WK_NAME]:
        if _vm_exists(name):
            print_info(f"Removing {name}...")
            remove_vm(name)

    print_ok("Cluster destroyed.")


def cmd_status(_args: argparse.Namespace):
    print_info("Registered VMs:")
    run([find_exe("VBoxManage"), "list", "vms"], check=False)

    print_info("\nRunning VMs:")
    run([find_exe("VBoxManage"), "list", "runningvms"], check=False)

    print_info("\nTalos nodes:")
    run([find_exe("talosctl"), "get", "nodes"], check=False)

    print_info("\nK8s nodes:")
    run([find_exe("kubectl"), "get", "nodes"], check=False)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Deploy qStack dev cluster (Talos + VirtualBox)"
    )
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
