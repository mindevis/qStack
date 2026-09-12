// Package mock provides mock provider implementations for testing.
package mock

import (
	"context"
	"fmt"
	"sync"

	"github.com/mindevis/qstack/pkg/types"
)

// Provider is a mock hypervisor provider for testing.
type Provider struct {
	mu   sync.RWMutex
	vms  map[string]*types.VM
	hosts map[string]*types.Host
}

// New creates a new mock provider.
func New() *Provider {
	return &Provider{
		vms:   make(map[string]*types.VM),
		hosts: make(map[string]*types.Host),
	}
}

// CreateVM creates a VM in the mock provider.
func (p *Provider) CreateVM(ctx context.Context, vm *types.VM) error {
	p.mu.Lock()
	defer p.mu.Unlock()
	p.vms[vm.ID] = vm
	return nil
}

// GetVM retrieves a VM by ID.
func (p *Provider) GetVM(ctx context.Context, id string) (*types.VM, error) {
	p.mu.RLock()
	defer p.mu.RUnlock()
	vm, ok := p.vms[id]
	if !ok {
		return nil, fmt.Errorf("vm %s not found", id)
	}
	return vm, nil
}

// ListVMs lists all VMs.
func (p *Provider) ListVMs(ctx context.Context) ([]*types.VM, error) {
	p.mu.RLock()
	defer p.mu.RUnlock()
	result := make([]*types.VM, 0, len(p.vms))
	for _, vm := range p.vms {
		result = append(result, vm)
	}
	return result, nil
}

// DeleteVM deletes a VM by ID.
func (p *Provider) DeleteVM(ctx context.Context, id string) error {
	p.mu.Lock()
	defer p.mu.Unlock()
	delete(p.vms, id)
	return nil
}
