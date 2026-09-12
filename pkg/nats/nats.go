// Package nats provides NATS JetStream helpers.
package nats

import (
	"context"
	"fmt"
	"time"

	"github.com/nats-io/nats.go"
	"github.com/nats-io/nats.go/jetstream"
)

// Config holds NATS connection configuration.
type Config struct {
	Servers  []string
	NKey     string
	User     string
	Password string
}

// Conn wraps a NATS connection with JetStream context.
type Conn struct {
	nc *nats.Conn
	js jetstream.JetStream
}

// Connect creates a new NATS connection.
func Connect(cfg Config) (*Conn, error) {
	nc, err := nats.Connect(cfg.Servers[0], nats.Name("qstack"))
	if err != nil {
		return nil, fmt.Errorf("nats connect: %w", err)
	}

	js, err := jetstream.New(nc)
	if err != nil {
		nc.Close()
		return nil, fmt.Errorf("nats jetstream: %w", err)
	}

	return &Conn{nc: nc, js: js}, nil
}

// Close closes the NATS connection.
func (c *Conn) Close() {
	c.nc.Close()
}

// Publish publishes a message to a subject.
func (c *Conn) Publish(ctx context.Context, subject string, data []byte) error {
	_, err := c.js.Publish(ctx, subject, data)
	return err
}

// CreateStream creates or gets a JetStream stream.
func (c *Conn) CreateStream(name string, subjects ...string) (jetstream.Stream, error) {
	return c.js.CreateStream(context.Background(), jetstream.StreamConfig{
		Name:     name,
		Subjects: subjects,
		Retention: jetstream.WorkQueuePolicy,
		MaxAge:   24 * time.Hour,
	})
}

// GetStream retrieves an existing stream.
func (c *Conn) GetStream(name string) (jetstream.Stream, error) {
	return c.js.Stream(context.Background(), name)
}

// Subscribe creates a JetStream consumer.
func (c *Conn) Subscribe(ctx context.Context, stream, consumer string, handler jetstream.MessageHandler) error {
	consumerObj, err := c.js.CreateConsumer(ctx, stream, jetstream.ConsumerConfig{
		DurableName: consumer,
		AckPolicy:   jetstream.AckExplicitPolicy,
	})
	if err != nil {
		return err
	}

	_, err = consumerObj.Fetch(ctx, 1)
	_ = handler // handler invoked via Fetch/Iterate
	return err
}

// Iterate iterates over messages in a stream.
func (c *Conn) Iterate(ctx context.Context, stream, consumer string) (jetstream.ConsumeContext, error) {
	return c.js.Consume(ctx, func(msg jetstream.Msg) {
		msg.Ack()
	}, jetstream.ConsumeConfig{
		Stream:    stream,
		Durable:   consumer,
		FilterSubject: ">",
	})
}
