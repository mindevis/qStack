#!/usr/bin/env python3
"""
deploy.py — Deploy/Tear down qStack dev environment (Talos on VirtualBox).

Usage:
  python deploy.py --up           # Deploy single node (1 VM)
  python deploy.py --up --multi   # Deploy multi node (1 CP + 1 Worker VM)
  python deploy.py --down         # Destroy cluster
  python deploy.py --status       # Check status
"""

from __future__ import annotations

import argparse
import glob
import os
import platform
import shutil
import subprocess
import sys
import time
import tempfile
from pathlib import Path
from typing import Optional

# ── Config ────────────────────────────────────────────────────────────────────

TALOS_VERSION = "v1.9.0"
IMAGE_ID = "ac16e32e83ab2de680fab908ca0e18516e427dd469d5fc61829f8f03e0983649"
NETWORK = "192.168.56.0/24"
BASE_IP = "192.168.56"
CLUSTER_NAME = "qStack"
VM_RAM = 8192  # 8GB for single node is plenty
VM_CPU = 4
VM_DISK = 40960  # 40GB
ISO_URL = f"https://factory.talos.dev/image/{IMAGE_ID}/{TALOS_VERSION}/metal-amd64-dev.iso"


# ── Helpers ──────────────────────────────────────────────────────────────────

def find_exe(name: str, search_dirs: Optional[list[str]] = None) -> str:
    """Find executable in PATH or common Windows dirs."""
    # Try direct PATH
    cmd = shutil.which(name)
    if cmd:
        return cmd

    # Fall back to common dirs
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
    return name  # Return original name so it fails later with "not found"


def run(cmd: list[str], check: bool = True, timeout: int = 60) -> str:
    """Run command, return stdout."""
    print(f"  > {' '.join(cmd[:5])}...")
    r = subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout,
    )
    out = (r.stdout + r.stderr).strip()
    if check and r.returncode != 0 and "not found" in out:
        print(f"  ERROR: Command not found: {cmd[0]}")
        sys.exit(1)
    return out


def print_step(n: int, msg: str):
    print(f"\n[{n}] {msg}")


def print_info(msg: str):
    print(f"  ℹ {msg}")


# ── Deploy Logic ─────────────────────────────────────────────────────────────

def download_iso() -> str:
    """Download Talos ISO if not present."""
    iso_name = f"talos-{TALOS_VERSION}-metal-amd64-dev.iso"
    iso_path = Path(iso_name)
    if iso_path.exists():
        print_info(f"ISO already exists: {iso_name}")
        return str(iso_path)

    print_info("Downloading Talos ISO (200MB)...")
    # Use aria2c if available, else curl
    downloader = shutil.which("aria2c") or shutil.which("curl")
    if not downloader:
        print("  ERROR: curl or aria2c not found")
        sys.exit(1)

    if "aria2c" in downloader:
        run([downloader, "-s4", "-x4", "-o", iso_name, ISO_URL], check=False)
    else:
        # curl -L -o
        run([downloader, "-L", "-o", iso_name, ISO_URL], check=False)

    if not iso_path.exists():
        print("  ERROR: ISO download failed")
        sys.exit(1)
    print_info(f"ISO downloaded: {iso_name}")
    return str(iso_path)


def create_vm(name: str, ip: str, iso_path: str):
    """Create a VirtualBox VM."""
    vdi = f"{name}.vdi"

    print_info(f"Creating VM: {name} ({ip})")
    run([find_exe("VBoxManage"), "createvm", "--name", name, "--register"])
    run([find_exe("VBoxManage"), "modifyvm", name, "--memory", str(VM_RAM), "--cpus", str(VM_CPU), "--ioapic", "on"])
    run([find_exe("VBoxManage"), "modifyvm", name, "--nic1", "natnetwork"])
    run([find_exe("VBoxManage"), "modifyvm", name, "--nat-network1", "natnet0"])
    run([find_exe("VBoxManage"), "modifyvm", name, "--nat-localhostproxy1", "on"])
    run([find_exe("VBoxManage"), "modifyvm", name, "--nicpromisc1", "deny"])

    # Storage
    run([find_exe("VBoxManage"), "storagectl", name, "--name", "SATA", "--add", "sata"])
    if not Path(vdi).exists():
        run([find_exe("VBoxManage"), "createhd", "--filename", vdi, "--size", str(VM_DISK)])
    run([find_exe("VBoxManage"), "storageattach", name, "--storagectl", "SATA", "--port", "0", "--device", "0", "--type", "hdd", "--medium", vdi])
    # Attach ISO
    run([find_exe("VBoxManage"), "storageattach", name, "--storagectl", "SATA", "--port", "1", "--device", "0", "--type", "dvddrive", "--medium", iso_path])


def setup_network():
    """Setup NAT network."""
    print_info("Setting up NAT network...")
    run([find_exe("VBoxManage"), "natnetwork", "remove", "--netname", "natnet0"], check=False)
    run([find_exe("VBoxManage"), "natnetwork", "add", "--netname", "natnet0", "--network", NETWORK, "--ipv6", "off", "--autoconfig", "off"])


def wait_for_boot(name: str, ip: str, timeout: int = 180):
    """Wait for Talos API (port 50000) to be ready."""
    print_info(f"Waiting for {name} to boot ({ip}:50000)...")
    start = time.time()
    while time.time() - start < timeout:
        # Try to connect via talosctl
        r = subprocess.run(
            [find_exe("talosctl"), "ping", "--nodes", ip],
            capture_output=True, text=True, timeout=10,
        )
        if "ok" in r.stdout.lower() or "success" in r.stdout.lower():
            print_info(f"{name} is ready!")
            return True
        time.sleep(5)
    print(f"  WARNING: Timed out waiting for {name} ({timeout}s). Proceeding anyway.")
    return False


def gen_config(ip: str, hostname: str, workers: list[str] = None):
    """Generate Talos config."""
    print_info("Generating Talos config...")
    cmd = [
        find_exe("talosctl"), "gen", "config", CLUSTER_NAME, f"{ip}:6443",
        "--output", "talos-cluster",
        "--install-image", f"factory.talos.dev/installer/{IMAGE_ID}/{TALOS_VERSION}",
        "--hostname", hostname,
    ]
    if workers:
        for wk in workers:
            cmd.extend(["--worker-endpoint", wk])
    run(cmd)


def apply_config(ip: str, role: str):
    """Apply config to node."""
    print_info(f"Applying {role} config to {ip}...")
    run([
        find_exe("talosctl"), "apply-config",
        "--file", f"talos-cluster/machines/{role}.yaml",
        "--nodes", ip,
    ])


def bootstrap(ip: str):
    """Bootstrap cluster."""
    print_info("Bootstrapping cluster...")
    run([find_exe("talosctl"), "bootstrap", "--nodes", ip])


def get_kubeconfig(ip: str):
    """Get kubeconfig."""
    print_info("Getting kubeconfig...")
    run([find_exe("talosctl"), "kubeconfig", "--nodes", ip, os.path.expanduser("~/.kube/config")])
    print_info("✅ kubeconfig saved to ~/.kube/config")


def verify_cluster():
    """Verify nodes."""
    print_info("Verifying cluster...")
    run([find_exe("kubectl"), "get", "nodes", "-o", "wide"])


def untaint_master():
    """Untaint master to allow pods."""
    print_info("Untainting master node...")
    run([find_exe("kubectl"), "taint", "nodes", "--all", "node-role.kubernetes.io/control-plane-", "--all", "node-role.kubernetes.io/master-", "--overwrite"])


# ── Commands ─────────────────────────────────────────────────────────────────

def cmd_up(args):
    print_step(1, "Download ISO")
    iso_path = download_iso()

    print_step(2, "Setup Network")
    setup_network()

    print_step(3, "Create VMs")
    ip_cp = f"{BASE_IP}.10"
    hostname_cp = f"{CLUSTER_NAME}-cp-00"

    if args.multi:
        ip_wk = f"{BASE_IP}.20"
        hostname_wk = f"{CLUSTER_NAME}-wk-00"
        create_vm(hostname_cp, ip_cp, iso_path)
        create_vm(hostname_wk, ip_wk, iso_path)
    else:
        create_vm(hostname_cp, ip_cp, iso_path)

    print_step(4, "Start VMs")
    run([find_exe("VBoxManage"), "startvm", hostname_cp, "--type", "headless"])
    if args.multi:
        run([find_exe("VBoxManage"), "startvm", hostname_wk, "--type", "headless"])

    print_step(5, "Wait for boot")
    wait_for_boot(hostname_cp, ip_cp)
    if args.multi:
        wait_for_boot(hostname_wk, ip_wk)

    print_step(6, "Generate Talos Config")
    if args.multi:
        gen_config(ip_cp, hostname_cp, workers=[ip_wk])
    else:
        gen_config(ip_cp, hostname_cp)

    print_step(7, "Apply Config")
    apply_config(ip_cp, "controlplane")
    if args.multi:
        apply_config(ip_wk, "worker")

    print_step(8, "Bootstrap Cluster")
    bootstrap(ip_cp)

    print_step(9, "Get Kubeconfig")
    get_kubeconfig(ip_cp)

    print_step(10, "Verify Cluster")
    verify_cluster()

    if not args.multi:
        untaint_master()

    print("\n✅ Cluster is ready! Use 'kubectl' to deploy qStack.")


def cmd_down(args):
    print_info("Shutting down VMs...")
    vms = [f"{CLUSTER_NAME}-cp-00"]
    if args.multi:
        vms.append(f"{CLUSTER_NAME}-wk-00")

    for vm in vms:
        print_info(f"Powering off {vm}...")
        run([find_exe("VBoxManage"), "controlvm", vm, "poweroff"], check=False)
        time.sleep(2)

    print_info("Deleting VMs...")
    for vm in vms:
        run([find_exe("VBoxManage"), "unregistervm", vm, "--delete"], check=False)

    print_info("Removing NAT network...")
    run([find_exe("VBoxManage"), "natnetwork", "remove", "--netname", "natnet0"], check=False)
    print("✅ Cluster destroyed.")


def cmd_status(args):
    print_info("Running VMs:")
    run([find_exe("VBoxManage"), "list", "runningvms"], check=False)
    print_info("\nTalos Nodes:")
    run([find_exe("talosctl"), "get", "nodes"], check=False)
    print_info("\nK8s Nodes:")
    run([find_exe("kubectl"), "get", "nodes"], check=False)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Deploy qStack dev environment")
    parser.add_argument("--up", action="store_true", help="Deploy cluster")
    parser.add_argument("--down", action="store_true", help="Destroy cluster")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--multi", action="store_true", help="Deploy 1 CP + 1 Worker (default: 1 node)")
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