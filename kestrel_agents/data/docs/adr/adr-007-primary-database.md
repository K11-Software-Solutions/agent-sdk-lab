---
title: "ADR-007: Primary database"
type: adr
status: accepted
updated: 2024-05-02
---
## Decision
PostgreSQL 16 on Amazon RDS is the primary database for all product data.

## Reasons
PostgreSQL gives us transactions, JSON columns and mature tooling. RDS handles backups, patching and Multi-AZ failover.
