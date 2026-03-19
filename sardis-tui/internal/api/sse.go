package api

import (
	"encoding/json"
	"fmt"
	"time"

	"github.com/r3labs/sse/v2"
)

// SSEStream manages the Server-Sent Events connection
type SSEStream struct {
	client    *sse.Client
	baseURL   string
	Events    chan EvalEvent
	Connected chan bool
	Errors    chan error
	done      chan struct{}
}

// NewSSEStream creates and starts an SSE stream
func NewSSEStream(baseURL string) *SSEStream {
	s := &SSEStream{
		baseURL:   baseURL,
		Events:    make(chan EvalEvent, 100),
		Connected: make(chan bool, 10),
		Errors:    make(chan error, 10),
		done:      make(chan struct{}),
	}
	return s
}

// Start begins listening to the SSE stream
func (s *SSEStream) Start() {
	go s.connect()
}

func (s *SSEStream) connect() {
	for {
		select {
		case <-s.done:
			return
		default:
		}

		s.client = sse.NewClient(s.baseURL + "/stream")

		err := s.client.SubscribeRaw(func(msg *sse.Event) {
			eventType := string(msg.Event)
			data := string(msg.Data)

			switch eventType {
			case "connected", "":
				if data == "" || eventType == "connected" {
					select {
					case s.Connected <- true:
					default:
					}
				}
			case "evaluation":
				var event EvalEvent
				if err := json.Unmarshal([]byte(data), &event); err == nil {
					select {
					case s.Events <- event:
					default:
						// drop event if channel full
					}
				}
			default:
				// try parsing as evaluation anyway
				var event EvalEvent
				if err := json.Unmarshal(msg.Data, &event); err == nil {
					select {
					case s.Events <- event:
					default:
					}
				}
			}
		})

		if err != nil {
			select {
			case s.Errors <- fmt.Errorf("SSE error: %w", err):
			default:
			}
			select {
			case s.Connected <- false:
			default:
			}
		}

		// wait before reconnecting
		select {
		case <-s.done:
			return
		case <-time.After(3 * time.Second):
		}
	}
}

// Stop closes the SSE stream
func (s *SSEStream) Stop() {
	close(s.done)
}
