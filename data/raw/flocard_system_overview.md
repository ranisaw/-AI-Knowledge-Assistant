# FloCard Enterprise System Overview

## What is FloCard?
FloCard is our core enterprise digital identity and smart networking platform. It replaces legacy business cards and paper credentials with dynamic, cryptographically signed digital profiles paired with hardware NFC smart badges and real-time enterprise telemetry.

## Core Capabilities
- **Digital Business Profiles**: Real-time verifiable contact cards synced automatically with Workday and Azure Active Directory.
- **NFC Tap & Share**: Zero-click profile sharing compatible with iOS and Android devices without requiring mobile app installations.
- **Enterprise Lead Analytics**: Tracks interaction events, team networking metrics, and CRM pipeline attribution directly to Salesforce and HubSpot.
- **Role-Based Access Control (RBAC)**: Enforces departmental permissions (Engineering, Sales, Executive) for profile disclosures and privacy boundaries.

## System Architecture
FloCard is built on an event-driven microservices architecture:
1. **Frontend Experience**: Next.js 14 web application and React Native mobile companion.
2. **Identity & Auth Service**: Go-based microservice issuing OIDC and JWT tokens with ed25519 digital signatures.
3. **Telemetry & Ingestion Engine**: Python FastAPI microservice publishing event streams to Kafka topics (`flocard.events.v1`).
4. **Data Persistence**: PostgreSQL for transactional state, Redis 7 for sub-millisecond profile caching, and Pinecone for vector discovery.

## FloCard SLA & Operations
- Production uptime guarantee: 99.95% availability.
- P1 Incidents: Target MTTR < 45 minutes. Contact `#flocard-eng-oncall` on Slack.
