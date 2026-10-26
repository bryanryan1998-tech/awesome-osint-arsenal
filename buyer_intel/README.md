# GrazeWays buyer intelligence

This dependency-free Python module helps organize **manually researched**
business prospects and prioritize them for further review. It does not search
the web, verify records against external services, send email, or contact
people.

## Run

From the repository root, using Python 3.10 or newer:

```bash
python3 -m buyer_intel validate
python3 -m buyer_intel rank --product beef
python3 -m buyer_intel rank --product beef --json
python3 -m buyer_intel rank --input path/to/buyers.json --product lamb
```

The default dataset is fictional and uses reserved `.invalid` domains and
addresses. No credentials or real customer information are included.

## Data format

Provide a JSON list of records. Each record requires `company`, `country`,
`buyer_types`, and `products`. `sources` is a list of dated evidence objects
with `type`, `url`, and `checked_on` (`YYYY-MM-DD`). A business email is
optional; use `email_status: "verified"` only when it has been independently
verified. The module does not perform that verification.

Example:

```json
[
  {
    "company": "Fictional Example Importer",
    "country": "Exampleland",
    "buyer_types": ["Importer"],
    "products": ["beef"],
    "public_business_email": "purchasing@example.invalid",
    "email_status": "unverified",
    "sources": [
      {
        "type": "trade_data",
        "url": "https://source.example.invalid/record/1",
        "checked_on": "2026-10-20"
      }
    ]
  }
]
```

## Explainable ranking

For the requested product, the module awards:

- 35 points for an exact product-label match (case-insensitive)
- 20 points for an importer, distributor, wholesaler, or processor role
- 20 points when a `trade_data` or `customs_record` source is recorded
- 15 points when an active `business_registry` source is recorded
- 10 points for a business email explicitly marked `verified`

The score is a review-priority aid, not proof of purchase intent, company
legitimacy, import activity, email deliverability, or product suitability.
Keep source URLs and check dates accurate, and independently confirm important
claims using the original source.

## Tests

```bash
python3 -m unittest discover -s buyer_intel/tests -v
```
