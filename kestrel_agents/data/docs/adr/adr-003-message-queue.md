---
title: "ADR-003: Message queue"
type: adr
status: superseded
superseded_by: adr/adr-009-message-queue
updated: 2023-02-10
---
## Decision
We will use RabbitMQ as our message queue for background jobs and service events.

## Reasons
The team has RabbitMQ experience, and it supports the routing patterns we need.
