#!/usr/bin/env python3
"""
check_deps.py — Pre-flight check and cluster config generator for qStack dev environment.

Checks:
  - Installed tools: VirtualBox, talosctl, kubectl, go, docker
  - System requirements: RAM (≥16GB), CPU (≥8 cores), disk space (≥80GB)

Generates:
  - cluster.yaml — cluster config (nodes, IPs, VM specs, Talos images)
  - setup.sh   — one-shot deploy script (VBoxManage + talosctl bootstrap)
  - talosconfig — talosctl context config

Usage:
  python check_deps.py                  # Check only
  python check_deps.py --generate       # Check + generate cluster.yaml + setup.sh
  python check_deps.py --generate --workers 2  # Custom worker count
"""

from __future__ import annotations

import argparse
import os
import platform
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


# ── Defaults ──────────────────────────────────────────────────────────────────

TALOS_VERSION = "v1.9.0"
IMAGE_ID = "ac16e32e83ab2de680fab908ca0e18516e427dd469d5fc61829f8f03e0983649"
NETWORK = "192.168.56.0/24"
BASE_IP = "192.168.56"
MIN_RAM_GB = 16
MIN_CPU = 8
MIN_DISK_GB = 80


# ── Data ──────────────────────────────────────────────────────────────────────

@dataclass
class Tool:
    name: str
    check_cmd: list[str]
    optional: bool = False
    description: str = ""
    install_hint: str = ""


@dataclass
class Node:
    hostname: str
    ip: str
    ram_mb: int
    cpus: int
    disk_gb: int
    role: str  # "controlplane" or "worker"


@dataclass
class ClusterConfig:
    name: str = "qStack"
    talos_version: str = TALOS_VERSION
    image_id: str = IMAGE_ID
    network: str = NETWORK
    cpus_per_node: int = 2
    ram_per_node_mb: int = 4096
    disk_per_node_gb: int = 40
    controlplane_count: int = 1
    worker_count: int = 1
    nodes: list[Node] = field(default_factory=list)


TOOLS: list[Tool] = [
    Tool(
        "VirtualBox",
        ["VBoxManage", "--version"],
        description="Virtual machine provider",
        install_hint='choco install virtualbox --params "/ExtensionPack"',
    ),
    Tool(
        "talosctl",
        ["talosctl", "--version"],
        description="Talos CLI",
        install_hint="choco install talosctl",
    ),
    Tool(
        "kubectl",
        ["kubectl", "--version", "--client"],
        description="Kubernetes CLI",
        install_hint="choco install kubernetes-cli",
    ),
    Tool(
        "go",
        ["go", "version"],
        description="Go toolchain",
        install_hint="choco install go",
    ),
    Tool(
        "docker",
        ["docker", "--version"],
        description="Docker (local infra)",
        install_hint="choco install docker-desktop",
    ),
    Tool("git", ["git", "--version"], description="Git"),
    Tool("curl", ["curl", "--version"], optional=True, description="HTTP client"),
    Tool("make", ["make", "--version"], optional=True, description="Build automation"),
]


# ── Checks ────────────────────────────────────────────────────────────────────

def run_cmd(cmd: list[str], timeout: int = 10) -> tuple[bool, str]:
    """Run command, return (success, output)."""
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
        return r.returncode == 0, (r.stdout + r.stderr).strip()
    except FileNotFoundError:
        return False, "not found"
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, str(e)


def run_powershell(ps_cmd: str) -> str:
    """Run a PowerShell command and return output (Windows only)."""
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=10,
        )
        return r.stdout.strip()
    except Exception:
        return ""


def check_tools() -> list[tuple[str, bool, str]]:
    """Check all tools. Return list of (name, found, output)."""
    results = []
    for tool in TOOLS:
        ok, out = run_cmd(tool.check_cmd)
        label = tool.name
        if ok:
            label = f"{tool.name} ✓"
        elif tool.optional:
            label = f"{tool.name} (optional)"
        else:
            label = f"{tool.name} ✗"
        results.append((label, ok, out))
    return results


def get_system_info() -> dict:
    """Get RAM, CPU, disk info."""
    ram_gb = 0
    cpus = 0
    free_gb = 0

    if platform.system() == "Windows":
        # Write .ps1 to temp file — avoids bash $variable expansion in git-bash
        import tempfile
        ps1_script = (
            '$os = Get-CimInstance Win32_OperatingSystem;\n'
            '$cpu = Get-CimInstance Win32_Processor;\n'
            '$disk = Get-CimInstance Win32_LogicalDisk | Where-Object { $_.DeviceID -eq "C:" };\n'
            '$memGB = [math]::Round($os.TotalVisibleMemorySize/1MB, 1);\n'
            '$cores = ($cpu | Measure-Object -Property NumberOfCores -Sum).Sum;\n'
            '$freeGB = [math]::Round($disk.FreeSpace/1GB, 0);\n'
            'Write-Output "$memGB,$cores,$freeGB"\n'
        )
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ps1', delete=False, encoding='utf-8') as f:
            f.write(ps1_script)
            ps1_path = f.name
        try:
            r = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive",
                 "-ExecutionPolicy", "Bypass", "-File", ps1_path],
                capture_output=True, text=True, timeout=10,
            )
            out = r.stdout.strip()
        finally:
            os.unlink(ps1_path)
        if out:
            out = out.replace("\ufeff", "").strip()
            parts = out.split(",")
            if len(parts) >= 3:
                try:
                    ram_gb = float(parts[0].strip())
                    cpus = int(parts[1].strip())
                    free_gb = int(float(parts[2].strip()))
                except (ValueError, IndexError):
                    pass
        if cpus == 0:
            cpus = os.cpu_count() or 0
    else:
        try:
            r = subprocess.run(["free", "-g"], capture_output=True, text=True, timeout=5)
            parts = r.stdout.strip().split("\n")
            if len(parts) > 1:
                ram_gb = int(parts[1].split()[1])
        except Exception:
            ram_gb = 0
        cpus = os.cpu_count() or 0
        try:
            r = subprocess.run(["df", "-BG", "/"], capture_output=True, text=True, timeout=5)
            for line in r.stdout.split("\n")[1:]:
                parts = line.split()
                if parts:
                    free = parts[3].replace("G", "")
                    free_gb = int(free)
        except Exception:
            free_gb = 0

    return {
        "ram_gb": ram_gb,
        "cpus": cpus,
        "free_disk_gb": free_gb,
    }


def check_system() -> list[tuple[str, bool]]:
    """Check system requirements."""
    info = get_system_info()
    checks = [
        (f"RAM: {info['ram_gb']:.1f} GB (min {MIN_RAM_GB} GB)", info["ram_gb"] >= MIN_RAM_GB),
        (f"CPU: {info['cpus']} cores (min {MIN_CPU})", info["cpus"] >= MIN_CPU),
        (f"Disk: {info['free_disk_gb']:.0f} GB free (min {MIN_DISK_GB} GB)", info["free_disk_gb"] >= MIN_DISK_GB),
    ]
    return checks


# ── Config Generator ──────────────────────────────────────────────────────────

def generate_nodes(config: ClusterConfig) -> list[Node]:
    """Generate node list based on config."""
    nodes = []
    # Control plane nodes
    for i in range(config.controlplane_count):
        nodes.append(Node(
            hostname=f"{config.name}-cp-{i:02d}",
            ip=f"{BASE_IP}.{10 + i}",
            ram_mb=config.ram_per_node_mb,
            cpus=config.cpus_per_node,
            disk_gb=config.disk_per_node_gb,
            role="controlplane",
        ))
    # Worker nodes
    for i in range(config.worker_count):
        nodes.append(Node(
            hostname=f"{config.name}-wk-{i:02d}",
            ip=f"{BASE_IP}.{20 + i}",
            ram_mb=config.ram_per_node_mb,
            cpus=config.cpus_per_node,
            disk_gb=config.disk_per_node_gb,
            role="worker",
        ))
    config.nodes = nodes
    return nodes


def generate_cluster_yaml(config: ClusterConfig) -> str:
    """Generate cluster.yaml."""
    lines = [
        "# Generated by check_deps.py — DO NOT EDIT MANUALLY",
        f"# qStack dev cluster on Talos Linux + VirtualBox",
        "",
        f"name: {config.name}",
        f"talos_version: {config.talos_version}",
        f"image_id: {config.image_id}",
        f"network: {config.network}",
        "",
        'kubernetes_version: "1.31"',
        "",
        "nodes:",
    ]
    for node in config.nodes:
        lines.extend([
            f"  - hostname: {node.hostname}",
            f"    role: {node.role}",
            f"    ip: {node.ip}",
            f"    ram_mb: {node.ram_mb}",
            f"    cpus: {node.cpus}",
            f"    disk_gb: {node.disk_gb}",
        ])

    lines.extend([
        "",
        "addons:",
        "  longhorn: true",
        "  metallb:",
        "    enabled: true",
        f"    pool: {BASE_IP}.200-{BASE_IP}.250",
    ])
    return "\n".join(lines)


def generate_setup_sh(config: ClusterConfig) -> str:
    """Generate setup.sh — one-shot deployment script."""
    cp_nodes = [n for n in config.nodes if n.role == "controlplane"]
    wk_nodes = [n for n in config.nodes if n.role == "worker"]
    cp_ip = cp_nodes[0].ip
    install_image = f"factory.talos.dev/installer/{config.image_id}/{config.talos_version}"

    lines = [
        "#!/usr/bin/env bash",
        "# Generated by check_deps.py — qStack dev cluster setup",
        "# Usage: bash setup.sh  (or ./setup.sh after chmod +x)",
        "set -euo pipefail",
        "",
        f'TALOS_VERSION="{config.talos_version}"',
        f'IMAGE_ID="{config.image_id}"',
        f'NETWORK="{config.network}"',
        f'CLUSTER_NAME="{config.name}"',
        "",
        "echo '=== 1. Creating VirtualBox NAT network ==='",
        'VBoxManage natnetwork remove --netname natnet0 2>/dev/null || true',
        f'VBoxManage natnetwork add --netname natnet0 --network {config.network} --ipv6 off --autoconfig off',
        "",
        "echo '=== 2. Creating VMs ==='",
    ]

    # Create VMs
    for node in config.nodes:
        vdi = f"{node.hostname}.vdi"
        lines.extend([
            "",
            f'# --- {node.hostname} ({node.role}) ---',
            f'VBoxManage createvm --name "{node.hostname}" --register',
            f'VBoxManage modifyvm "{node.hostname}" --memory {node.ram_mb} --cpus {node.cpus} --ioapic on',
            f'VBoxManage modifyvm "{node.hostname}" --nic1 natnetwork',
            f'VBoxManage modifyvm "{node.hostname}" --nat-network1 "natnet0"',
            f'VBoxManage modifyvm "{node.hostname}" --nat-localhostproxy1 on',
            f'VBoxManage storagectl "{node.hostname}" --name "SATA" --add sata',
            f'VBoxManage createhd --filename "{vdi}" --size {node.disk_gb * 1024}',
            f'VBoxManage storageattach "{node.hostname}" --storagectl "SATA" --port 0 --device 0 --type hdd --medium "{vdi}"',
        ])

    # Download ISO
    lines.extend([
        "",
        "echo '=== 3. Downloading Talos ISO ==='",
        'ISO="talos-${TALOS_VERSION}-metal-amd64-dev.iso"',
        "if [ ! -f \"$ISO\" ]; then",
        '  echo "Downloading Talos ISO..."',
        '  curl -LO "https://factory.talos.dev/image/${IMAGE_ID}/${TALOS_VERSION}/metal-amd64-dev.iso"',
        '  mv "metal-amd64-dev.iso" "$ISO"',
        "fi",
        "",
        "echo '=== 4. Attaching ISO to VMs ==='",
    ])
    for node in config.nodes:
        lines.append(
            f'VBoxManage storageattach "{node.hostname}" '
            f'--storagectl "SATA" --port 1 --device 0 --type dvddrive --medium "$ISO"'
        )

    # Start VMs
    lines.extend([
        "",
        "echo '=== 5. Starting VMs ==='",
    ])
    for node in config.nodes:
        lines.append(f'VBoxManage startvm "{node.hostname}" --type headless')

    # Wait and generate config
    lines.extend([
        "",
        'echo "Waiting 120s for VMs to boot..."',
        "sleep 120",
        "",
        "echo '=== 6. Generating Talos config ==='",
        "mkdir -p talos-cluster",
    ])

    # talosctl gen config <cluster-name> <endpoint>
    # https://www.talos.dev/latest/learn-more/cli/#talosctl-gen-config
    lines.append(f'talosctl gen config {config.name} {cp_ip}:6443 \\')
    lines.append(f'  --output talos-cluster \\')
    lines.append(f'  --install-image "{install_image}" \\')
    lines.append(f'  --hostname {cp_nodes[0].hostname} \\')

    for i, wk in enumerate(wk_nodes):
        is_last = (i == len(wk_nodes) - 1)
        trailing = "" if is_last else " \\"
        lines.append(f'  --worker-endpoint {wk.ip}{trailing}')
        lines.append(f'  --worker-hostname {wk.hostname}{trailing}')

    # Apply config
    lines.extend([
        "",
        "echo '=== 7. Applying config to nodes ==='",
    ])
    for node in config.nodes:
        role_dir = "controlplane" if node.role == "controlplane" else "worker"
        lines.append(
            f'talosctl apply-config --file talos-cluster/machines/{role_dir}.yaml '
            f'--nodes {node.ip}'
        )

    # Bootstrap + verify
    lines.extend([
        "",
        "echo '=== 8. Bootstrap cluster ==='",
        f'talosctl bootstrap --nodes {cp_ip}',
        "",
        "echo '=== 9. Getting kubeconfig ==='",
        f'talosctl kubeconfig --nodes {cp_ip} ~/.kube/config',
        "",
        "echo '=== 10. Verifying cluster ==='",
        "kubectl get nodes",
        "",
        "echo ''",
        'echo "✅ Cluster ready! Deploy qStack with:"',
        'echo "  kubectl apply -f k8s/common/"',
        'echo "  kubectl apply -f k8s/api/"',
        'echo "  kubectl apply -f k8s/compute/"',
        'echo "  ... (see docs/ for full deploy guide)"',
        "",
    ])
    return "\n".join(lines)


def generate_talosctl_config(config: ClusterConfig) -> str:
    """Generate talosconfig for easy access."""
    cp = config.nodes[0] if config.nodes else None
    if not cp:
        return ""
    lines = [
        "# Generated by check_deps.py",
        "context: default",
        "",
        "contexts:",
        "  default:",
        "    endpoints:",
    ]
    for node in config.nodes:
        if node.role == "controlplane":
            lines.append(f"      - {node.ip}")
    lines.extend([
        "    ca: /etc/talos/certs/ca.crt",
        "    crt: /etc/talos/certs/server.crt",
        "    key: /etc/talos/certs/server.key",
    ])
    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def print_header(text: str):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="qStack dev environment pre-flight check")
    parser.add_argument("--generate", action="store_true", help="Generate cluster config + setup script")
    parser.add_argument("--workers", type=int, default=1, help="Number of worker nodes (default: 1)")
    parser.add_argument("--cpus", type=int, default=2, help="CPU cores per VM (default: 2)")
    parser.add_argument("--ram", type=int, default=4096, help="RAM per VM in MB (default: 4096)")
    parser.add_argument("--disk", type=int, default=40, help="Disk per VM in GB (default: 40)")
    parser.add_argument("--output", "-o", default=".", help="Output directory (default: .)")
    args = parser.parse_args()

    print_header("qStack Dev Environment — Dependency Check")

    # ── Tools ──
    print("📦 Installed tools:")
    tool_results = check_tools()
    all_tools_ok = True
    for name, found, out in tool_results:
        status = "✓" if found else ("—" if "optional" in name.lower() else "✗")
        if not found and "✗" == status:
            all_tools_ok = False
            for t in TOOLS:
                if t.name in name and not t.optional and t.install_hint:
                    print(f"  {status} {name}")
                    print(f"      → {t.install_hint}")
                    break
            else:
                print(f"  {status} {name}")
        else:
            print(f"  {status} {name}")

    # ── System ──
    print("\n💻 System requirements:")
    sys_checks = check_system()
    all_sys_ok = True
    for desc, ok in sys_checks:
        status = "✓" if ok else "✗"
        if not ok:
            all_sys_ok = False
        print(f"  {status} {desc}")

    # ── Summary ──
    print(f"\n{'─'*60}")
    if all_tools_ok and all_sys_ok:
        print("✅ All checks passed!")
    else:
        missing = [name for name, found, _ in tool_results if not found and "✗" in name]
        if missing:
            print(f"⚠️  Missing required tools: {', '.join(missing)}")
        if not all_sys_ok:
            print("⚠️  System requirements not met")
        print("\nInstall missing tools, then re-run this script.")

    # ── Generate ──
    if args.generate:
        print_header("Generating cluster configuration")

        config = ClusterConfig(
            worker_count=args.workers,
            cpus_per_node=args.cpus,
            ram_per_node_mb=args.ram,
            disk_per_node_gb=args.disk,
        )
        generate_nodes(config)

        out_dir = Path(args.output)
        out_dir.mkdir(parents=True, exist_ok=True)

        # cluster.yaml
        cluster_yaml = generate_cluster_yaml(config)
        cluster_path = out_dir / "cluster.yaml"
        cluster_path.write_text(cluster_yaml, encoding="utf-8")
        print(f"📄 {cluster_path}")

        # setup.sh
        setup_sh = generate_setup_sh(config)
        setup_path = out_dir / "setup.sh"
        setup_path.write_text(setup_sh, encoding="utf-8")
        if platform.system() != "Windows":
            setup_path.chmod(0o755)
        print(f"📄 {setup_path}")

        # talosconfig
        talos_config = generate_talosctl_config(config)
        talos_path = out_dir / "talosconfig"
        talos_path.write_text(talos_config, encoding="utf-8")
        print(f"📄 {talos_path}")

        # Summary
        total_nodes = len(config.nodes)
        total_ram = sum(n.ram_mb for n in config.nodes) // 1024
        total_cpus = sum(n.cpus for n in config.nodes)
        print(f"\n📊 Cluster summary:")
        print(f"   Nodes: {total_nodes} (1 CP + {args.workers} worker{'s' if args.workers > 1 else ''})")
        print(f"   Total RAM: {total_ram} GB ({args.ram} MB / node)")
        print(f"   Total CPUs: {total_cpus} ({args.cpus} / node)")
        print(f"   Network: {NETWORK}")
        print(f"\n🚀 Next steps:")
        print(f"   1. Review cluster.yaml")
        print(f"   2. Run: bash {setup_path}")
        print(f"   3. After setup: talosctl --talosconfig {talos_path} get nodes")

    print()


if __name__ == "__main__":
    main()
