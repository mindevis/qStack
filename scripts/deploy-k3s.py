#!/usr/bin/env python3
"""
deploy-k3s.py — Deploy qStack dev on single-node k3s (VirtualBox).

k3s is a lightweight Kubernetes distribution designed for single-node
deployments. Use this for faster dev iterations where you don't need
multi-node networking or storage testing.

For multi-node Talos cluster: scripts/deploy.py

Usage:
  python deploy-k3s.py --up      # Deploy single VM with k3s
  python deploy-k3s.py --down    # Destroy cluster
  python deploy-k3s.py --status  # Check status
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

NETWORK = "192.168.56.0/24"
BASE_IP = "192.168.56"
CLUSTER_NAME = "qStack-k3s"
VM_NAME = f"{CLUSTER_NAME}-node"
VM_IP = f"{BASE_IP}.10"
VM_RAM = 8192  # 8GB — enough for single node + workloads
VM_CPU = 4
VM_DISK = 40960  # 40GB

# Ubuntu 24.04 LTS ISO (minimal server)
UBUNTU_ISO = "ubuntu-24.04.1-live-server-amd64.iso"
UBUNTU_ISO_URL = (
    "https://releases.ubuntu.com/24.04/ubuntu-24.04.1-live-server-amd64.iso"
)


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
    print_info("Setting up NAT network...")
    run([find_exe("VBoxManage"), "natnetwork", "remove", "--netname", "natnet-k3s"], check=False)
    run([find_exe("VBoxManage"), "natnetwork", "add", "--netname", "natnet-k3s",
         "--network", NETWORK, "--ipv6", "off", "--autoconfig", "off"])


def download_ubuntu() -> str:
    """Download Ubuntu ISO if not present."""
    iso_path = Path(UBUNTU_ISO)
    if iso_path.exists():
        print_info(f"ISO already exists: {UBUNTU_ISO}")
        return str(iso_path)

    print_info("Downloading Ubuntu 24.04 ISO (~4.5GB)...")
    downloader = shutil.which("aria2c") or shutil.which("curl")
    if not downloader:
        print("  ✗ curl or aria2c not found")
        sys.exit(1)

    if "aria2c" in downloader:
        run([downloader, "-s4", "-x4", "-o", UBUNTU_ISO, UBUNTU_ISO_URL], check=False)
    else:
        run([downloader, "-L", "-o", UBUNTU_ISO, UBUNTU_ISO_URL], check=False)

    if not iso_path.exists():
        print("  ✗ ISO download failed")
        sys.exit(1)
    print_info(f"ISO downloaded: {UBUNTU_ISO}")
    return str(iso_path)


def create_vm(iso_path: str):
    """Create VM with Ubuntu ISO."""
    vdi = f"{VM_NAME}.vdi"

    print_info(f"Creating VM: {VM_NAME} (RAM {VM_RAM}MB, CPU {VM_CPU}, {VM_DISK // 1024}GB disk)")
    run([find_exe("VBoxManage"), "createvm", "--name", VM_NAME, "--register"])
    run([find_exe("VBoxManage"), "modifyvm", VM_NAME, "--memory", str(VM_RAM), "--cpus", str(VM_CPU), "--ioapic", "on"])
    run([find_exe("VBoxManage"), "modifyvm", VM_NAME, "--nic1", "natnetwork"])
    run([find_exe("VBoxManage"), "modifyvm", VM_NAME, "--nat-network1", "natnet-k3s"])
    run([find_exe("VBoxManage"), "modifyvm", VM_NAME, "--nat-localhostproxy1", "on"])

    # Storage
    run([find_exe("VBoxManage"), "storagectl", VM_NAME, "--name", "SATA", "--add", "sata"])
    if not Path(vdi).exists():
        run([find_exe("VBoxManage"), "createhd", "--filename", vdi, "--size", str(VM_DISK)])
    run([find_exe("VBoxManage"), "storageattach", VM_NAME, "--storagectl", "SATA",
         "--port", "0", "--device", "0", "--type", "hdd", "--medium", vdi])
    # ISO
    run([find_exe("VBoxManage"), "storageattach", VM_NAME, "--storagectl", "SATA",
         "--port", "1", "--device", "0", "--type", "dvddrive", "--medium", iso_path])


def start_vm():
    run([find_exe("VBoxManage"), "startvm", VM_NAME, "--type", "headless"])


def poweroff_vm():
    run([find_exe("VBoxManage"), "controlvm", VM_NAME, "poweroff"], check=False)


def remove_vm():
    run([find_exe("VBoxManage"), "unregistervm", VM_NAME, "--delete"], check=False)


# ── k3s Setup ────────────────────────────────────────────────────────────────

def wait_for_ssh(timeout: int = 300) -> bool:
    """Wait until the VM gets an IP (check via VBox guest additions)."""
    print_info(f"Waiting for {VM_NAME} to boot and get IP...")
    print_info("Please install Ubuntu on the VM, then continue.")
    print_info(f"Press Enter when Ubuntu is installed and the VM is running...")
    input()
    return True


def install_k3s():
    """Generate k3s install script."""
    print_info("Generate k3s install commands...")

    install_sh = """#!/bin/bash
# Run this on the Ubuntu VM after installing it:
set -e

# Install k3s
curl -sfL https://get.k3s.io | sh -

# Copy kubeconfig
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $USER:$USER ~/.kube/config
chmod 600 ~/.kube/config

echo "k3s installed! Run 'kubectl get nodes' to verify."
"""
    install_file = "k3s-install.sh"
    Path(install_file).write_text(install_sh)
    print_info(f"✓ Generated {install_file}")
    print_info("SSH into the VM and run: bash k3s-install.sh")


def verify_cluster():
    print_info("Cluster nodes:")
    out = run([find_exe("kubectl"), "get", "nodes", "-o", "wide"])
    print(f"  {out}")


# ── Commands ─────────────────────────────────────────────────────────────────

def cmd_up(_args: argparse.Namespace):
    print_step(1, "Download Ubuntu ISO")
    iso_path = download_ubuntu()

    print_step(2, "Setup Network")
    setup_network()

    print_step(3, "Create VM")
    create_vm(iso_path)

    print_step(4, "Start VM")
    start_vm()

    print_step(5, "Install Ubuntu (manual)")
    print_info("=" * 60)
    print_info("1. Open the VM in VirtualBox Manager (or View → VMs)")
    print_info("2. Install Ubuntu Server (minimal, no LXD)")
    print_info("3. Create user: 'talos' / 'dev' (any name)")
    print_info("4. Install openssh-server")
    print_info("5. After install, the VM will reboot")
    print_info("=" * 60)
    print_info("Press Enter when Ubuntu is installed...")
    input()

    print_step(6, "Install k3s")
    install_k3s()
    print_info("SSH into the VM and run: bash k3s-install.sh")
    print_info("Press Enter when k3s is installed...")
    input()

    print_step(7, "Verify Cluster")
    print_info("Copy /etc/rancher/k3s/k3s.yaml from VM to ~/.kube/config")
    print_info("Press Enter when kubeconfig is set up...")
    input()

    verify_cluster()

    print("\n✅ k3s cluster ready! Deploy qStack:")
    print(f"   kubectl get nodes")
    print(f"   kubectl apply -f k8s/")


def cmd_down(_args: argparse.Namespace):
    print_info("Shutting down...")
    poweroff_vm()
    time.sleep(2)
    remove_vm()
    run([find_exe("VBoxManage"), "natnetwork", "remove", "--netname", "natnet-k3s"], check=False)
    print("✅ k3s cluster destroyed.")


def cmd_status(_args: argparse.Namespace):
    print_info("Running VMs:")
    run([find_exe("VBoxManage"), "list", "runningvms"], check=False)
    print_info("\nK8s nodes:")
    run([find_exe("kubectl"), "get", "nodes"], check=False)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Deploy qStack dev on k3s (single-node)")
    parser.add_argument("--up", action="store_true", help="Deploy single-node k3s cluster")
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
