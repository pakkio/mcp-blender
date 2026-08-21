.PHONY: build test lint install clean

BIN_EXT := $(if $(filter windows,$(shell go env GOOS)),.exe,)

build:
	go build -o bin/mcp-blender-pp-cli$(BIN_EXT) ./cmd/mcp-blender-pp-cli

test:
	go test ./...

lint:
	golangci-lint run

install:
	go install ./cmd/mcp-blender-pp-cli

clean:
	rm -rf bin/

build-mcp:
	go build -o bin/mcp-blender-pp-mcp$(BIN_EXT) ./cmd/mcp-blender-pp-mcp

install-mcp:
	go install ./cmd/mcp-blender-pp-mcp

build-all: build build-mcp
