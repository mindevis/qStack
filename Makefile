.PHONY: all build-all test-all proto infra-up infra-down deps tidy clean

all: tidy build-all test-all

# Install Go workspace dependencies
deps:
	go work sync

# Tidy all modules
tidy:
	go mod tidy
	cd cmd/qstack-api && go mod tidy
	cd cmd/qstack-storage && go mod tidy
	cd cmd/qstack-network && go mod tidy
	cd cmd/qstack-image && go mod tidy
	cd cmd/qstack-billing && go mod tidy
	cd cmd/qstack-backup && go mod tidy
	cd cmd/qstack-ai && go mod tidy
	cd cmd/qstack-agent && go mod tidy

# Generate Go code from .proto files
proto:
	protoc \
		--go_out=. --go_opt=paths=source_relative \
		--go-grpc_out=. --go-grpc_opt=paths=source_relative \
		proto/qstack/v1/*.proto

# Build all services
build-all: build-api build-storage build-network build-image build-billing build-backup build-ai build-agent

build-api:
	go build -o bin/qstack-api ./cmd/qstack-api

build-storage:
	go build -o bin/qstack-storage ./cmd/qstack-storage

build-network:
	go build -o bin/qstack-network ./cmd/qstack-network

build-image:
	go build -o bin/qstack-image ./cmd/qstack-image

build-billing:
	go build -o bin/qstack-billing ./cmd/qstack-billing

build-backup:
	go build -o bin/qstack-backup ./cmd/qstack-backup

build-ai:
	go build -o bin/qstack-ai ./cmd/qstack-ai

build-agent:
	go build -o bin/qstack-agent ./cmd/qstack-agent

# Run all tests
test-all:
	go test ./pkg/...
	cd cmd/qstack-api && go test ./...
	cd cmd/qstack-storage && go test ./...
	cd cmd/qstack-network && go test ./...
	cd cmd/qstack-image && go test ./...
	cd cmd/qstack-billing && go test ./...
	cd cmd/qstack-backup && go test ./...
	cd cmd/qstack-ai && go test ./...
	cd cmd/qstack-agent && go test ./...

# Infrastructure services (PostgreSQL, NATS, Prometheus, Grafana, Loki, GlitchTip)
infra-up:
	docker compose up -d

infra-down:
	docker compose down

# Clean build artifacts
clean:
	rm -rf bin/
