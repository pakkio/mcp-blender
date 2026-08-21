// Package wsbridge is a minimal client for the mcp-blender WebSocket bridge
// (extension/bridge/server.py in the mcp-blender project). The bridge is a
// local, single-connection JSON-RPC-shaped protocol -- not HTTP -- so this
// package intentionally does not reuse internal/client's HTTP transport. Each
// call dials fresh, sends one request envelope, waits for the matching
// response, and closes: the CLI is a one-shot process, so there is no need to
// mirror the Python bridge client's persistent-connection/reconnect-backoff
// state machine.
package wsbridge

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/gorilla/websocket"
)

// envelope mirrors the wire shape used by mcp_server/src/mcp_blender/bridge.py:
// request  = {"id": "...", "method": "...", "params": {...}}
// response = {"id": "...", "result": {...}}  or  {"id": "...", "error": {...}}
type envelope struct {
	ID     string          `json:"id"`
	Method string          `json:"method,omitempty"`
	Params any             `json:"params,omitempty"`
	Result json.RawMessage `json:"result,omitempty"`
	Error  *BridgeError    `json:"error,omitempty"`
}

// BridgeError mirrors the {"type", "message", "details"} error shape raised
// by BridgeError on the Python side (mcp_server/src/mcp_blender/errors.py).
type BridgeError struct {
	Type    string `json:"type"`
	Message string `json:"message"`
	Details any    `json:"details,omitempty"`
}

func (e *BridgeError) Error() string {
	if e.Type != "" {
		return fmt.Sprintf("%s: %s", e.Type, e.Message)
	}
	return e.Message
}

// Call opens a connection to the Blender bridge at wsURL, sends one
// {method, params} request, and returns the decoded "result" field (or the
// bridge's structured error). timeout bounds both the dial and the
// round-trip; HEAVY_REQUEST_TIMEOUT_S-class Blender operations (bake, render,
// remesh) need a much longer value than the default request timeout.
func Call(ctx context.Context, wsURL, method string, params any, timeout time.Duration) (json.RawMessage, error) {
	if timeout <= 0 {
		timeout = 15 * time.Second
	}

	dialCtx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	dialer := websocket.Dialer{HandshakeTimeout: timeout}
	conn, _, err := dialer.DialContext(dialCtx, wsURL, nil)
	if err != nil {
		return nil, fmt.Errorf("connecting to Blender bridge at %s (is Blender running with the mcp-blender addon enabled?): %w", wsURL, err)
	}
	defer conn.Close()

	requestID := fmt.Sprintf("pp-%d", time.Now().UnixNano())
	if params == nil {
		params = map[string]any{}
	}
	req := envelope{ID: requestID, Method: method, Params: params}

	if err := conn.WriteJSON(req); err != nil {
		return nil, fmt.Errorf("sending '%s' request to Blender bridge: %w", method, err)
	}

	deadline := time.Now().Add(timeout)
	if ctxDeadline, ok := ctx.Deadline(); ok && ctxDeadline.After(deadline) == false {
		deadline = ctxDeadline
	}
	_ = conn.SetReadDeadline(deadline)

	for {
		var resp envelope
		if err := conn.ReadJSON(&resp); err != nil {
			return nil, fmt.Errorf("waiting for '%s' response from Blender bridge: %w", method, err)
		}
		if resp.ID != requestID {
			// Not our response (shouldn't happen on a fresh single-request
			// connection, but stay defensive); keep waiting for a match.
			continue
		}
		if resp.Error != nil {
			return nil, resp.Error
		}
		return resp.Result, nil
	}
}
