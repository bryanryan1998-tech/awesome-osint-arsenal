import unittest

from buyer_intel.core import rank_buyers, validate_records


def sample_record(**overrides):
    record = {
        "company": "Fictional Test Buyer",
        "country": "Exampleland",
        "buyer_types": ["Importer"],
        "products": ["beef"],
        "public_business_email": "buyer@example.invalid",
        "email_status": "verified",
        "sources": [
            {
                "type": "trade_data",
                "url": "https://source.example.invalid/trade/1",
                "checked_on": "2026-10-20",
            },
            {
                "type": "business_registry",
                "url": "https://source.example.invalid/registry/1",
                "checked_on": "2026-10-20",
                "status": "active",
            },
        ],
    }
    record.update(overrides)
    return record


class BuyerIntelTests(unittest.TestCase):
    def test_full_evidence_scores_100(self):
        ranked = rank_buyers([sample_record()], "Beef")
        self.assertEqual(ranked[0].score, 100)
        self.assertEqual(ranked[0].company, "Fictional Test Buyer")

    def test_only_exact_product_match_gets_product_points(self):
        ranked = rank_buyers(
            [sample_record(products=["lamb"], sources=[], email_status="unverified")],
            "beef",
        )
        self.assertEqual(ranked[0].score, 20)
        self.assertNotIn("product match (+35)", ranked[0].reasons)

    def test_sorted_by_score_then_company(self):
        lower = sample_record(company="Fictional Beta", sources=[], email_status="unverified")
        higher = sample_record(company="Fictional Zeta")
        equal_name_a = sample_record(company="Fictional Alpha")
        ranked = rank_buyers([lower, higher, equal_name_a], "beef")
        self.assertEqual(
            [buyer.company for buyer in ranked],
            ["Fictional Alpha", "Fictional Zeta", "Fictional Beta"],
        )

    def test_rejects_invalid_source_date_and_email(self):
        errors = validate_records(
            [
                sample_record(
                    public_business_email="not-an-email",
                    sources=[
                        {
                            "type": "trade_data",
                            "url": "https://source.example.invalid/trade/1",
                            "checked_on": "not-a-date",
                        }
                    ],
                )
            ]
        )
        self.assertTrue(any("public_business_email" in error for error in errors))
        self.assertTrue(any("checked_on" in error for error in errors))

    def test_rejects_verified_status_without_email(self):
        errors = validate_records([sample_record(public_business_email=None)])
        self.assertTrue(any("requires a business email" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
