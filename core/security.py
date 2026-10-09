"""
Security and Compliance utilities:
- Regex-based PII redaction (emails, phone numbers, employee IDs, secrets)
- Token verification and authentication helpers
- Ethical and safe AI usage compliance statement
"""
import re
from typing import Tuple, Dict, Any
from core.config import settings

# Regex patterns for sensitive data redaction
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b')
PHONE_PATTERN = re.compile(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b')
SSN_OR_GOV_ID = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
EMPLOYEE_ID_PATTERN = re.compile(r'\b(?:EMP|USER|CORP)-[0-9]{4,8}\b', re.IGNORECASE)
API_KEY_PATTERN = re.compile(r'\b(?:sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{20,}|key-[a-zA-Z0-9]{16,})\b')

ETHICAL_AI_DISCLAIMER = """
[ETHICAL & RESPONSIBLE AI USAGE POLICY]
This assistant is strictly intended to aid internal knowledge discovery and engineering onboarding.
1. Grounding: All generated statements must be directly supported by internal documentation citations.
2. Confidentiality: Customer personal data, proprietary cryptographic secrets, and unredacted PII are barred from prompt context.
3. Human Oversight: Responses provided are advisory. Engineers must verify architectural and security-critical implementations against authoritative source code.
""".strip()


def redact_pii(text: str) -> Tuple[str, Dict[str, int]]:
    """
    Scrub sensitive Personal Identifiable Information (PII) and secret tokens from text.
    Returns:
        (sanitized_text, redaction_counts)
    """
    if not settings.enable_pii_redaction or not text:
        return text, {}

    counts = {
        "emails": len(EMAIL_PATTERN.findall(text)),
        "phones": len(PHONE_PATTERN.findall(text)),
        "gov_ids": len(SSN_OR_GOV_ID.findall(text)),
        "employee_ids": len(EMPLOYEE_ID_PATTERN.findall(text)),
        "api_keys": len(API_KEY_PATTERN.findall(text)),
    }

    sanitized = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", text)
    sanitized = PHONE_PATTERN.sub("[REDACTED_PHONE]", sanitized)
    sanitized = SSN_OR_GOV_ID.sub("[REDACTED_GOV_ID]", sanitized)
    sanitized = EMPLOYEE_ID_PATTERN.sub("[REDACTED_EMP_ID]", sanitized)
    sanitized = API_KEY_PATTERN.sub("[REDACTED_SECRET]", sanitized)

    active_counts = {k: v for k, v in counts.items() if v > 0}
    return sanitized, active_counts


def verify_token(token: str | None) -> bool:
    """Validate bearer token or API key against configured secret."""
    if not settings.require_auth:
        return True
    if not token:
        return False
    # Support 'Bearer <token>' prefix or raw key
    cleaned_token = token.replace("Bearer ", "").strip() if token.startswith("Bearer ") else token.strip()
    return cleaned_token == settings.api_secret_key
