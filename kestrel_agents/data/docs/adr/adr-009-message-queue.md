---
title: "ADR-009: Move background jobs to Amazon SQS"
type: adr
status: accepted
updated: 2025-11-20
---
## Decision
Amazon SQS replaces RabbitMQ for background jobs and service events. New services must publish to SQS. This supersedes ADR-003.

## Reasons
Running RabbitMQ clusters took about one engineer-week per quarter. SQS is managed by AWS, scales without capacity planning, and integrates with IAM.

## Consequences
Ordering is only guaranteed with FIFO queues, which have lower throughput. Services that need strict ordering must use FIFO queues explicitly.
