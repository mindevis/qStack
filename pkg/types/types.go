package types

import (
	"time"
)

// State represents the lifecycle state of a VM.
type State string

const (
	StatePending     State = "pending"
	StateRunning     State = "running"
	StateStopped     State = "stopped"
	StatePaused      State = "paused"
	StateError       State = "error"
	StateMigrating   State = "migrating"
	StateDestroying  State = "destroying"
	StateProvisioned State = "provisioned"
)

// VM represents a virtual machine in the system.
type VM struct {
	ID          string    `json:"id"`
	Name        string    `json:"name"`
	TenantID    string    `json:"tenant_id"`
	ClusterID   string    `json:"cluster_id"`
	HostID      string    `json:"host_id"`
	State       State     `json:"state"`
	CPU         int       `json:"cpu"`
	MemoryMB    int       `json:"memory_mb"`
	DiskSizeGB  int       `json:"disk_size_gb"`
	ImageID     string    `json:"image_id"`
	NetworkIDs  []string  `json:"network_ids"`
	VolumeIDs   []string  `json:"volume_ids"`
	Tags        map[string]string `json:"tags"`
	CreatedAt   time.Time `json:"created_at"`
	UpdatedAt   time.Time `json:"updated_at"`
	StartedAt   *time.Time `json:"started_at,omitempty"`
	IPs         []string  `json:"ips,omitempty"`
	DesiredState State    `json:"desired_state"`
	LastError   string    `json:"last_error,omitempty"`
}

// Host represents a hypervisor host.
type Host struct {
	ID           string    `json:"id"`
	Name         string    `json:"name"`
	ClusterID    string    `json:"cluster_id"`
	Address      string    `json:"address"`
	State        HostState `json:"state"`
	CPUTotal     int       `json:"cpu_total"`
	CPUUsed      int       `json:"cpu_used"`
	MemoryTotalMB int      `json:"memory_total_mb"`
	MemoryUsedMB  int      `json:"memory_used_mb"`
	DiskTotalGB   int      `json:"disk_total_gb"`
	DiskUsedGB    int      `json:"disk_used_gb"`
	VMCount      int       `json:"vm_count"`
	LastHeartbeat time.Time `json:"last_heartbeat"`
	Tags         map[string]string `json:"tags"`
	CreatedAt    time.Time `json:"created_at"`
}

type HostState string

const (
	HostStateOnline     HostState = "online"
	HostStateOffline    HostState = "offline"
	HostStateMaintenance HostState = "maintenance"
	HostStateDegraded   HostState = "degraded"
)

// Volume represents a block storage volume.
type Volume struct {
	ID           string    `json:"id"`
	Name         string    `json:"name"`
	TenantID     string    `json:"tenant_id"`
	SizeGB       int       `json:"size_gb"`
	PoolID       string    `json:"pool_id"`
	Backend      string    `json:"backend"` // libvirt, ceph-rbd, iscsi, local
	State        string    `json:"state"`
	AttachedToVM string    `json:"attached_to_vm,omitempty"`
	CreatedAt    time.Time `json:"created_at"`
}

// Network represents a virtual network.
type Network struct {
	ID          string    `json:"id"`
	Name        string    `json:"name"`
	TenantID    string    `json:"tenant_id"`
	CIDR        string    `json:"cidr"`
	Gateway     string    `json:"gateway"`
	Backend     string    `json:"backend"` // libvirt, macvlan
	SubnetCount int       `json:"subnet_count"`
	VLAN        int       `json:"vlan,omitempty"`
	MTU         int       `json:"mtu"`
	CreatedAt   time.Time `json:"created_at"`
}

// Image represents a VM image/template.
type Image struct {
	ID        string    `json:"id"`
	Name      string    `json:"name"`
	TenantID  string    `json:"tenant_id"`
	SizeGB    int       `json:"size_gb"`
	Format    string    `json:"format"` // qcow2, raw, vmdk, vhd
	Backend   string    `json:"backend"` // local, ceph-rbd, s3
	State     string    `json:"state"`
	OS        string    `json:"os"`
	Arch      string    `json:"arch"`
	Checksum  string    `json:"checksum"` // SHA-256
	Visibility string   `json:"visibility"` // public, private, shared
	Tags      []string  `json:"tags"`
	CreatedAt time.Time `json:"created_at"`
}
