// Package types provides shared domain types with protobuf marshaling.
package types

import "time"

// ProtoTime converts time.Time to protobuf Timestamp.
func ProtoTime(t time.Time) *time.Time {
	if t.IsZero() {
		return nil
	}
	return &t
}

// ValidState checks if the state is a known VM state.
func ValidState(s State) bool {
	switch s {
	case StatePending, StateRunning, StateStopped, StatePaused,
		StateError, StateMigrating, StateDestroying, StateProvisioned:
		return true
	}
	return false
}
