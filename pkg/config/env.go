// Package config provides environment-based configuration loading.
package config

import (
	"fmt"
	"os"
	"strconv"
	"strings"
)

// Config holds application configuration loaded from environment.
type Config struct {
	Prefix string
	data   map[string]string
}

// LoadEnv loads configuration from environment variables with the given prefix.
// E.g. LoadEnv("QSTACK_API") loads QSTACK_API_PORT, QSTACK_API_GRPC_ADDR, etc.
func LoadEnv(prefix string) (*Config, error) {
	if prefix == "" {
		return nil, fmt.Errorf("prefix is required")
	}

	cfg := &Config{
		Prefix: prefix,
		data:   make(map[string]string),
	}

	for _, env := range os.Environ() {
		parts := strings.SplitN(env, "=", 2)
		if len(parts) != 2 {
			continue
		}
		key := parts[0]
		val := parts[1]

		if strings.HasPrefix(key, prefix+"_") {
			// Strip prefix and convert to lowercase
			field := strings.ToLower(strings.TrimPrefix(key, prefix+"_"))
			cfg.data[field] = val
		}
	}

	return cfg, nil
}

// GetString returns a string value by field name.
func (c *Config) GetString(field, defaultValue string) string {
	if v, ok := c.data[field]; ok {
		return v
	}
	return defaultValue
}

// GetInt returns an integer value by field name.
func (c *Config) GetInt(field string, defaultValue int) int {
	if v, ok := c.data[field]; ok {
		n, err := strconv.Atoi(v)
		if err == nil {
			return n
		}
	}
	return defaultValue
}

// GetBool returns a boolean value by field name.
func (c *Config) GetBool(field string, defaultValue bool) bool {
	if v, ok := c.data[field]; ok {
		b, err := strconv.ParseBool(v)
		if err == nil {
			return b
		}
	}
	return defaultValue
}

// Get returns the raw value for a field.
func (c *Config) Get(field string) (string, bool) {
	v, ok := c.data[field]
	return v, ok
}
