# Event-Driven Architecture Guide & Kafka Conventions

## Core Philosophy
To decouple core services, FloCard processes all state transitions through Apache Kafka event streams. Services must never perform synchronous HTTP mutations across domain boundaries.

## Kafka Topic Naming Scheme
All Kafka topics must adhere strictly to the pattern:
`<domain>.<entity>.<version>.<action>`

Examples:
- `flocard.profile.v1.created`
- `flocard.telemetry.v1.tap_recorded`
- `flocard.billing.v2.subscription_renewed`

## Event Schema & Avro Serialization
All event payloads are serialized using Apache Avro schemas registered in our Confluent Schema Registry. Every event envelope must include:
```json
{
  "eventId": "evt_uuid4_unique",
  "timestamp": 1774501234,
  "producer": "flocard-profile-service",
  "schemaVersion": "1.4.0",
  "data": { ... }
}
```

## Dead Letter Queue (DLQ) & Retry Policy
Consumers encounter poisoned pills or transient dependency failures must follow the 3-tier backoff policy:
1. Immediate retry up to 3 attempts with exponential jitter.
2. If unresolved, route message to `<original_topic>.retry` with 5-minute delayed reprocessing.
3. If still failing after 3 delayed cycles, move message to `<original_topic>.dlq` and notify `#kafka-dlq-alerts`.
