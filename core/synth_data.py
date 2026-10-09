"""
Synthetic Data Generator for AI Knowledge Assistant.
Generates realistic internal enterprise documentation across 4 key themes:
1. Company Overview & Team FAQs (e.g. FloCard system, engineering handbook)
2. Technical Tutorials & API Snippets (e.g. Auth service, API gateway)
3. SOPs & Best Practices (e.g. Incident response runbook, code review SLAs)
4. Architecture Guides & Data Schemas (e.g. Database migrations, Event-driven streaming)

Outputs multiple formats: Markdown (.md), PDF (.pdf), Word (.docx), and CSV (.csv).
Each document is paired with structured metadata (title, tags, type, date).
"""
import os
import json
import csv
from pathlib import Path
from datetime import datetime
from core.config import settings


def _create_minimal_pdf(file_path: Path, title: str, paragraphs: list[str]):
    """
    Generate a valid, standards-compliant PDF 1.4 document without heavy external C-libraries.
    """
    def sanitize(text: str) -> str:
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    objects = []
    
    # 1: Catalog
    objects.append("1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj")
    # 2: Pages
    objects.append("2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj")
    # 3: Page
    objects.append("3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj")
    
    # Build text stream
    lines = [f"BT /F1 16 Tf 50 740 Td ({sanitize(title)}) Tj ET"]
    y = 710
    for p in paragraphs:
        # Wrap simple lines
        words = p.split()
        current_line = []
        for word in words:
            current_line.append(word)
            if len(" ".join(current_line)) > 75:
                text_to_print = " ".join(current_line[:-1])
                lines.append(f"BT /F1 10 Tf 50 {y} Td ({sanitize(text_to_print)}) Tj ET")
                y -= 15
                current_line = [word]
                if y < 60:
                    break
        if current_line and y >= 60:
            lines.append(f"BT /F1 10 Tf 50 {y} Td ({sanitize(' '.join(current_line))}) Tj ET")
            y -= 22
        if y < 60:
            break

    stream_content = "\n".join(lines)
    stream_length = len(stream_content.encode("utf-8"))
    
    # 4: Stream object
    objects.append(f"4 0 obj\n<< /Length {stream_length} >>\nstream\n{stream_content}\nendstream\nendobj")
    # 5: Font object
    objects.append("5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj")
    
    # Build PDF file
    header = "%PDF-1.4\n"
    body = ""
    xref = ["xref\n0 6\n0000000000 65535 f \n"]
    offset = len(header.encode("utf-8"))
    
    for obj in objects:
        xref.append(f"{offset:010d} 00000 n \n")
        obj_bytes = (obj + "\n").encode("utf-8")
        offset += len(obj_bytes)
        body += obj + "\n"
        
    xref_str = "".join(xref)
    trailer = f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{offset}\n%%EOF"
    
    with open(file_path, "wb") as f:
        f.write((header + body + xref_str + trailer).encode("utf-8"))


def _create_docx(file_path: Path, title: str, sections: list[tuple[str, str]]):
    """
    Generate a Word (.docx) document using python-docx if available, or XML structure fallback.
    """
    try:
        from docx import Document
        doc = Document()
        doc.add_heading(title, level=0)
        for heading, body in sections:
            doc.add_heading(heading, level=2)
            doc.add_paragraph(body)
        doc.save(file_path)
    except ImportError:
        # Fallback text representation if docx isn't finished installing yet
        with open(file_path.with_suffix(".txt"), "w", encoding="utf-8") as f:
            f.write(f"# {title}\n\n")
            for h, b in sections:
                f.write(f"## {h}\n{b}\n\n")


def generate_synthetic_documents(output_dir: Path | None = None) -> list[dict]:
    """
    Generate the comprehensive set of mock onboarding and knowledge documents.
    """
    target_dir = output_dir or settings.raw_data_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    generated_records = []

    # 1. FloCard Overview (Markdown)
    flocard_md = target_dir / "flocard_system_overview.md"
    flocard_content = """# FloCard Enterprise System Overview

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
"""
    flocard_meta = {
        "title": "FloCard Enterprise System Overview",
        "tags": ["flocard", "architecture", "product-overview", "identity", "nfc"],
        "type": "overview",
        "date": "2026-01-15",
        "author": "FloCard Architecture Guild",
        "classification": "Internal"
    }
    flocard_md.write_text(flocard_content, encoding="utf-8")
    (target_dir / "flocard_system_overview.meta.json").write_text(json.dumps(flocard_meta, indent=2), encoding="utf-8")
    generated_records.append({"file": flocard_md.name, **flocard_meta})

    # 2. Engineering Handbook (Markdown)
    handbook_md = target_dir / "engineering_handbook.md"
    handbook_content = """# Engineering Handbook & Team Guidelines

## Working Principles
We optimize for high autonomy, transparent async communication, and relentless engineering quality.

## Core Hours & Communication
- **Core Collaboration Hours**: 10:00 AM – 3:00 PM local time across your timezone.
- **Primary Channels**:
  - `#engineering-general`: Cross-team announcements and celebrations.
  - `#eng-helpdesk`: Internal questions, CI/CD trouble, and tooling support.
  - `#incident-alerts`: Automated PagerDuty and Datadog monitoring notifications.
- **Email Usage**: Reserved strictly for formal contracts, external vendor discussions, and executive briefs. Use Slack for daily collaboration.

## Pull Request Guidelines & Code Review SLA
1. **PR Sizing**: Keep pull requests under 350 lines of diff whenever possible.
2. **Review SLA**: 
   - Standard PRs: Review feedback within 24 hours.
   - Hotfix / Blocking PRs: Review feedback within 2 hours with ping in `#eng-hotfixes`.
3. **Approvals**: Minimum of 2 peer approvals required prior to merging to `main`.
4. **CI Checks**: Unit test coverage must remain >= 80%. Automated linting and SonarQube quality gates must pass.

## Branch Naming Convention
- Feature branches: `feat/<jira-id>-short-description` (e.g., `feat/FLO-1024-nfc-telemetry`)
- Bug fixes: `fix/<jira-id>-short-description`
- Infrastructure: `infra/<jira-id>-short-description`
"""
    handbook_meta = {
        "title": "Engineering Handbook & Team Guidelines",
        "tags": ["handbook", "onboarding", "code-review", "sla", "workflow"],
        "type": "guide",
        "date": "2026-02-01",
        "author": "VP of Engineering",
        "classification": "Internal"
    }
    handbook_md.write_text(handbook_content, encoding="utf-8")
    (target_dir / "engineering_handbook.meta.json").write_text(json.dumps(handbook_meta, indent=2), encoding="utf-8")
    generated_records.append({"file": handbook_md.name, **handbook_meta})

    # 3. Auth Service API Tutorial (Markdown)
    auth_md = target_dir / "auth_service_api_tutorial.md"
    auth_content = """# Internal Authentication Service API Tutorial

## Overview
The Central Auth Service (`auth-core`) issues cryptographically signed JSON Web Tokens (JWT) for inter-service communication and user authentication across all engineering domains.

## Endpoints

### 1. Issue Service Token
- **Method**: `POST /api/v1/oauth/token`
- **Headers**: `Content-Type: application/json`
- **Payload**:
```json
{
  "client_id": "service-flocard-telemetry",
  "client_secret": "env_vault_secret_key",
  "grant_type": "client_credentials",
  "scope": "telemetry:write profiles:read"
}
```
- **Success Response (200 OK)**:
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsIn...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "rfr_98a7sd6f..."
}
```

### 2. Verify Token & Introspect
- **Method**: `POST /api/v1/oauth/introspect`
- **Headers**: `Authorization: Bearer <access_token>`
- **Response**:
```json
{
  "active": true,
  "sub": "service-flocard-telemetry",
  "scopes": ["telemetry:write", "profiles:read"],
  "exp": 1774500000
}
```

## Rate Limiting & Throttling
- Internal services: 10,000 requests per minute per IP.
- Public client gateways: 120 requests per minute per authenticated user.
- Status code 429 Too Many Requests includes `Retry-After` header in seconds.
"""
    auth_meta = {
        "title": "Internal Authentication Service API Tutorial",
        "tags": ["auth", "api", "jwt", "oauth", "security", "tutorial"],
        "type": "tutorial",
        "date": "2026-02-18",
        "author": "Security Engineering Team",
        "classification": "Confidential"
    }
    auth_md.write_text(auth_content, encoding="utf-8")
    (target_dir / "auth_service_api_tutorial.meta.json").write_text(json.dumps(auth_meta, indent=2), encoding="utf-8")
    generated_records.append({"file": auth_md.name, **auth_meta})

    # 4. SOP: Microservice Deployment (Word .docx)
    sop_docx = target_dir / "microservice_deployment_sop.docx"
    sop_sections = [
        ("1. Purpose & Scope", 
         "This Standard Operating Procedure defines the mandatory lifecycle steps for building, testing, and deploying containerized microservices to production Kubernetes clusters across AWS and Azure regions."),
        ("2. Pre-Deployment Verification", 
         "Before initiating any production deployment, the engineer must ensure: (1) Unit test pass rate is 100%, (2) Docker image is scanned by Trivy with zero CRITICAL or HIGH vulnerabilities, (3) Pull Request has been merged into main with signed commits."),
        ("3. Progressive Canary Deployment Protocol", 
         "All deployments leverage ArgoCD and progressive canary rollouts: Canary Phase 1 starts with 5% traffic routing for 15 minutes while monitoring Datadog error rates. If 5xx errors remain below 0.05%, Canary Phase 2 scales to 25% traffic for 30 minutes. Upon validation, 100% promotion executes automatically."),
        ("4. Automated Rollback Triggers", 
         "Canary progression aborts and triggers automatic rollbacks if: HTTP 5xx error rate exceeds 0.2%, P99 latency spikes above 800ms, or Pod crash-loop counter increments more than 3 times within 5 minutes.")
    ]
    _create_docx(sop_docx, "Standard Operating Procedure: Microservice Deployment", sop_sections)
    sop_meta = {
        "title": "Standard Operating Procedure: Microservice Deployment",
        "tags": ["sop", "deployment", "kubernetes", "canary", "devops", "ci-cd"],
        "type": "sop",
        "date": "2026-03-01",
        "author": "Platform & Cloud Infrastructure Guild",
        "classification": "Internal"
    }
    (target_dir / "microservice_deployment_sop.meta.json").write_text(json.dumps(sop_meta, indent=2), encoding="utf-8")
    generated_records.append({"file": sop_docx.name, **sop_meta})

    # 5. Incident Response Runbook (Word .docx)
    incident_docx = target_dir / "incident_response_runbook.docx"
    incident_sections = [
        ("Severity Levels Overview",
         "SEV-1 (Critical Outage): Core FloCard service down, customer data impacted, or zero authentication. MTTR target < 30 minutes. SEV-2 (Major Degradation): High latency (>2s), key integration failure, or analytics pipeline paused. MTTR target < 2 hours. SEV-3 (Minor): Non-blocking UI glitch or delayed background sync. MTTR target < 24 hours."),
        ("Incident Command Roles",
         "Incident Commander (IC): Coordinates triage and directs engineering investigation. Communications Lead (CL): Posts status updates to #incident-status every 15 minutes. Operations Lead (OL): Executes rollbacks, restarts, and infrastructure traffic rerouting."),
        ("Post-Mortem Policy & Blameless Reviews",
         "For all SEV-1 and SEV-2 incidents, a blameless post-mortem document must be drafted in Confluence within 48 business hours. The review meeting takes place weekly on Wednesdays to extract actionable prevention tickets.")
    ]
    _create_docx(incident_docx, "Production Incident Response Runbook", incident_sections)
    incident_meta = {
        "title": "Production Incident Response Runbook",
        "tags": ["incident", "runbook", "on-call", "sre", "post-mortem", "sev-1"],
        "type": "runbook",
        "date": "2026-03-05",
        "author": "Site Reliability Engineering (SRE)",
        "classification": "Internal"
    }
    (target_dir / "incident_response_runbook.meta.json").write_text(json.dumps(incident_meta, indent=2), encoding="utf-8")
    generated_records.append({"file": incident_docx.name, **incident_meta})

    # 6. IT Setup & Employee Perks (PDF)
    it_pdf = target_dir / "it_setup_and_employee_perks.pdf"
    it_paragraphs = [
        "Welcome to the Engineering Organization. This document outlines your hardware setup, network security requirements, and internal benefits.",
        "Hardware Provisioning: All engineers receive a 16-inch Apple MacBook Pro M3 Max (36GB RAM, 1TB SSD) or Dell XPS 15 (64GB RAM). Hardware refreshes occur every 24 months.",
        "Zero-Trust Network Access (ZTNA): Install Cloudflare WARP and authenticate with Okta single sign-on. Direct SSH to production servers is strictly prohibited; all cluster access requires Teleport bastion certificates.",
        "Wellness and Education Stipends: Every team member is entitled to a $1,500 annual Learning & Development budget for books, certifications, and technical conferences. You also receive a $100 monthly fitness and wellness reimbursement submitted through Expensify.",
        "Remote Work Setup Allowance: A one-time $1,000 home office setup allowance is provided to purchase an ergonomic chair, external 4K monitor, or standing desk."
    ]
    _create_minimal_pdf(it_pdf, "IT Setup, Security & Employee Perks Guide", it_paragraphs)
    it_meta = {
        "title": "IT Setup, Security & Employee Perks Guide",
        "tags": ["it", "hardware", "benefits", "vpn", "stipends", "onboarding"],
        "type": "guide",
        "date": "2026-01-20",
        "author": "People Operations & IT Support",
        "classification": "Internal"
    }
    (target_dir / "it_setup_and_employee_perks.meta.json").write_text(json.dumps(it_meta, indent=2), encoding="utf-8")
    generated_records.append({"file": it_pdf.name, **it_meta})

    # 7. Database Migration Protocol (PDF)
    db_pdf = target_dir / "database_migration_protocol.pdf"
    db_paragraphs = [
        "Database Migration Architecture Guide: Enforcing Zero-Downtime Schema Evolutions across PostgreSQL and DynamoDB.",
        "Principles of Zero-Downtime Migrations: All database migrations must follow the Expand and Contract pattern across multiple software releases. Direct dropping of columns or renaming tables in a single step is strictly prohibited.",
        "Phase 1 (Expand): Add the new nullable column or secondary table. Deploy backend code that writes to both old and new schemas while reading from the old schema.",
        "Phase 2 (Backfill): Execute an asynchronous batch backfill script during off-peak hours using our internal db-worker job queue.",
        "Phase 3 (Switch Read): Deploy software release to read from the new schema.",
        "Phase 4 (Contract): Remove legacy code pathways and safely deprecate the unused old column in a subsequent release cycle."
    ]
    _create_minimal_pdf(db_pdf, "Database Migration Protocol & Zero-Downtime Rules", db_paragraphs)
    db_meta = {
        "title": "Database Migration Protocol & Zero-Downtime Rules",
        "tags": ["database", "postgres", "migration", "architecture", "zero-downtime"],
        "type": "architecture",
        "date": "2026-02-25",
        "author": "Data Platform Guild",
        "classification": "Internal"
    }
    (target_dir / "database_migration_protocol.meta.json").write_text(json.dumps(db_meta, indent=2), encoding="utf-8")
    generated_records.append({"file": db_pdf.name, **db_meta})

    # 8. Company FAQ (CSV)
    faq_csv = target_dir / "company_faq.csv"
    faq_rows = [
        ["Question", "Category", "Answer", "Owner", "Last_Updated"],
        ["What is FloCard?", "Product", "FloCard is our core enterprise digital identity and smart networking platform leveraging NFC badges and real-time CRM telemetry.", "Product Management", "2026-01-10"],
        ["How do I request a new cloud sandbox?", "Infrastructure", "Open a ticket in Jira under the INFRA project using the Cloud Sandbox Request template. Approvals require your engineering manager.", "Cloud Platform", "2026-01-15"],
        ["What is our code review SLA?", "Engineering", "Standard PRs must receive review feedback within 24 hours. Critical hotfixes must be reviewed within 2 hours.", "Eng Leadership", "2026-02-01"],
        ["How do I report a SEV-1 production incident?", "Operations", "Immediately type /incident in any Slack channel or alert the on-call engineer via PagerDuty escalation policy.", "SRE Team", "2026-02-10"],
        ["Where do I find my health insurance and 401k details?", "HR & Benefits", "Log into the Gusto portal with your single sign-on credentials. Benefits documentation is under My Documents.", "People Ops", "2026-01-05"],
        ["Can I work remotely from another country?", "HR Policy", "Remote work abroad is permitted for up to 30 days per calendar year with prior approval from HR and tax compliance.", "Legal & People", "2026-02-20"]
    ]
    with open(faq_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(faq_rows)
    faq_meta = {
        "title": "Company Knowledge Base & Onboarding FAQs",
        "tags": ["faq", "onboarding", "hr", "operations", "policies", "flocard"],
        "type": "faq",
        "date": "2026-02-20",
        "author": "People Operations",
        "classification": "Internal"
    }
    (target_dir / "company_faq.meta.json").write_text(json.dumps(faq_meta, indent=2), encoding="utf-8")
    generated_records.append({"file": faq_csv.name, **faq_meta})

    # 9. Service Catalog & Ports (CSV)
    catalog_csv = target_dir / "service_catalog_and_ports.csv"
    catalog_rows = [
        ["Service_Name", "Internal_Port", "Protocol", "Health_Endpoint", "Primary_Team", "SLA_Tier"],
        ["flocard-auth-service", "8081", "HTTP/gRPC", "/healthz", "Security Guild", "Tier 1 (99.99%)"],
        ["flocard-telemetry-engine", "8082", "HTTP/Kafka", "/api/v1/health", "Data Pipeline", "Tier 1 (99.95%)"],
        ["flocard-profile-service", "8083", "gRPC", "/status", "Core Product", "Tier 1 (99.95%)"],
        ["flocard-reporting-worker", "8084", "HTTP", "/metrics", "BI & Analytics", "Tier 2 (99.90%)"],
        ["flocard-notification-dispatcher", "8085", "HTTP", "/health", "Platform Ops", "Tier 2 (99.90%)"]
    ]
    with open(catalog_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(catalog_rows)
    catalog_meta = {
        "title": "Engineering Microservice Catalog & Internal Ports",
        "tags": ["services", "ports", "microservices", "networking", "catalog"],
        "type": "infrastructure",
        "date": "2026-03-01",
        "author": "Core Architecture",
        "classification": "Confidential"
    }
    (target_dir / "service_catalog_and_ports.meta.json").write_text(json.dumps(catalog_meta, indent=2), encoding="utf-8")
    generated_records.append({"file": catalog_csv.name, **catalog_meta})

    # 10. Event-Driven Architecture Guide (Markdown)
    event_md = target_dir / "event_driven_architecture_guide.md"
    event_content = """# Event-Driven Architecture Guide & Kafka Conventions

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
"""
    event_meta = {
        "title": "Event-Driven Architecture Guide & Kafka Conventions",
        "tags": ["kafka", "events", "architecture", "dlq", "streaming", "microservices"],
        "type": "architecture",
        "date": "2026-03-10",
        "author": "Event Streaming Guild",
        "classification": "Internal"
    }
    event_md.write_text(event_content, encoding="utf-8")
    (target_dir / "event_driven_architecture_guide.meta.json").write_text(json.dumps(event_meta, indent=2), encoding="utf-8")
    generated_records.append({"file": event_md.name, **event_meta})

    print(f"Successfully generated {len(generated_records)} synthetic knowledge documents in: {target_dir}")
    return generated_records


if __name__ == "__main__":
    generate_synthetic_documents()
