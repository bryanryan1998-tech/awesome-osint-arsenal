"""Validation and transparent lead scoring for manually researched companies."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from typing import Any
from urllib.parse import urlparse

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_EMAIL_STATUSES = {"unverified", "verified", "rejected"}
_BUYER_TYPES = {"importer", "distributor", "wholesaler", "processor"}
_TRADE_SOURCE_TYPES = {"trade_data", "customs_record"}


@dataclass(frozen=True)
class RankedBuyer:
    company: str
    country: str
    score: int
    reasons: tuple[str, ...]
    public_business_email: str | None


def validate_records(records: Any) -> list[str]:
    """Return all schema problems found in a list of buyer records."""
    errors: list[str] = []
    if not isinstance(records, list):
        return ["root: expected a list of buyer records"]

    for index, record in enumerate(records):
        prefix = f"record {index + 1}"
        if not isinstance(record, dict):
            errors.append(f"{prefix}: expected an object")
            continue

        for field in ("company", "country"):
            if not isinstance(record.get(field), str) or not record[field].strip():
                errors.append(f"{prefix}: '{field}' must be a non-empty string")

        for field in ("buyer_types", "products"):
            value = record.get(field)
            if (
                not isinstance(value, list)
                or not value
                or any(not isinstance(item, str) or not item.strip() for item in value)
            ):
                errors.append(f"{prefix}: '{field}' must be a non-empty list of strings")

        email = record.get("public_business_email")
        if email is not None and (
            not isinstance(email, str) or not _EMAIL_RE.fullmatch(email.strip())
        ):
            errors.append(f"{prefix}: 'public_business_email' must be a valid email or null")

        email_status = record.get("email_status", "unverified")
        if not isinstance(email_status, str) or email_status not in _EMAIL_STATUSES:
            errors.append(
                f"{prefix}: 'email_status' must be one of "
                f"{', '.join(sorted(_EMAIL_STATUSES))}"
            )
        elif email_status == "verified" and not email:
            errors.append(f"{prefix}: verified email status requires a business email")

        sources = record.get("sources", [])
        if not isinstance(sources, list):
            errors.append(f"{prefix}: 'sources' must be a list")
            continue
        for source_index, source in enumerate(sources):
            source_prefix = f"{prefix}, source {source_index + 1}"
            if not isinstance(source, dict):
                errors.append(f"{source_prefix}: expected an object")
                continue

            source_type = source.get("type")
            if not isinstance(source_type, str) or not source_type.strip():
                errors.append(f"{source_prefix}: 'type' must be a non-empty string")

            url = source.get("url")
            parsed_url = urlparse(url) if isinstance(url, str) else None
            if (
                parsed_url is None
                or parsed_url.scheme not in {"http", "https"}
                or not parsed_url.netloc
            ):
                errors.append(f"{source_prefix}: 'url' must be an absolute HTTP(S) URL")

            if "status" in source and not isinstance(source["status"], str):
                errors.append(f"{source_prefix}: 'status' must be a string")

            checked_on = source.get("checked_on")
            try:
                if not isinstance(checked_on, str):
                    raise ValueError
                if date.fromisoformat(checked_on).isoformat() != checked_on:
                    raise ValueError
            except ValueError:
                errors.append(f"{source_prefix}: 'checked_on' must be a YYYY-MM-DD date")

    return errors


def rank_buyers(records: list[dict[str, Any]], product: str) -> list[RankedBuyer]:
    """Rank records by explicit product fit and documented evidence (maximum 100)."""
    if not product.strip():
        raise ValueError("product must not be empty")

    ranked: list[RankedBuyer] = []
    target = product.strip().casefold()
    for record in records:
        score = 0
        reasons: list[str] = []
        products = {item.strip().casefold() for item in record["products"]}
        buyer_types = {item.strip().casefold() for item in record["buyer_types"]}
        sources = record.get("sources", [])
        source_types = {source["type"].casefold() for source in sources}

        if target in products:
            score += 35
            reasons.append("product match (+35)")
        if buyer_types & _BUYER_TYPES:
            score += 20
            reasons.append("buyer type match (+20)")
        if source_types & _TRADE_SOURCE_TYPES:
            score += 20
            reasons.append("trade/customs source recorded (+20)")
        if any(
            source["type"].casefold() == "business_registry"
            and source.get("status", "").casefold() == "active"
            for source in sources
        ):
            score += 15
            reasons.append("active registry source recorded (+15)")
        if (
            record.get("public_business_email")
            and record.get("email_status", "unverified") == "verified"
        ):
            score += 10
            reasons.append("business email marked verified (+10)")

        ranked.append(
            RankedBuyer(
                company=record["company"],
                country=record["country"],
                score=score,
                reasons=tuple(reasons) or ("no matching evidence recorded",),
                public_business_email=record.get("public_business_email"),
            )
        )

    return sorted(ranked, key=lambda buyer: (-buyer.score, buyer.company.casefold()))
