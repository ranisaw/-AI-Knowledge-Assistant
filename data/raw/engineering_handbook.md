# Engineering Handbook & Team Guidelines

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
