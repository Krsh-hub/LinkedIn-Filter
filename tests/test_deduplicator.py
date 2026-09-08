"""Unit tests for URL normalization and deduplication logic."""

import unittest
import pandas as pd
from src.deduplicator import deduplicate_contacts, normalize_name_and_company
from src.utils import normalize_linkedin_url


class TestDeduplicator(unittest.TestCase):
    """Test suite for URL normalization and intelligent contact deduplication."""

    def test_url_normalization(self):
        """Test URL normalization stripping protocol, www, parameters, and trailing slashes."""
        u1 = "https://www.linkedin.com/in/example/"
        u2 = "https://linkedin.com/in/example"
        u3 = "http://www.linkedin.com/in/example?trk=test"
        u4 = "linkedin.com/in/example/"

        self.assertEqual(normalize_linkedin_url(u1), "linkedin.com/in/example")
        self.assertEqual(normalize_linkedin_url(u2), "linkedin.com/in/example")
        self.assertEqual(normalize_linkedin_url(u3), "linkedin.com/in/example")
        self.assertEqual(normalize_linkedin_url(u4), "linkedin.com/in/example")
        self.assertEqual(normalize_linkedin_url(""), "")
        self.assertEqual(normalize_linkedin_url(None), "")

    def test_deduplication_by_linkedin_url(self):
        """Test that records with equivalent LinkedIn URLs are merged."""
        df = pd.DataFrame([
            {
                "full_name": "Alice Smith",
                "company": "Acme Corp",
                "position": "CEO",
                "linkedin_url": "https://www.linkedin.com/in/alicesmith/",
                "email": "",
                "seniority_score": 98,
                "data_quality_score": 60,
            },
            {
                "full_name": "Alice Smith",
                "company": "Acme Corp",
                "position": "CEO & Founder",
                "linkedin_url": "https://linkedin.com/in/alicesmith",
                "email": "alice@acme.com",
                "seniority_score": 100,
                "data_quality_score": 80,
            }
        ])

        deduped, removed = deduplicate_contacts(df)
        self.assertEqual(removed, 1)
        self.assertEqual(len(deduped), 1)
        # Verify the email from second record was merged
        self.assertEqual(deduped.iloc[0]["email"], "alice@acme.com")
        self.assertEqual(deduped.iloc[0]["seniority_score"], 100)

    def test_deduplication_by_email(self):
        """Test that records with the same email are merged even if URLs are missing."""
        df = pd.DataFrame([
            {
                "full_name": "Bob Jones",
                "company": "Tech Innovations",
                "position": "CTO",
                "linkedin_url": "",
                "email": "bob@tech.io",
                "seniority_score": 98,
                "data_quality_score": 60,
            },
            {
                "full_name": "Bob Jones",
                "company": "",
                "position": "CTO",
                "linkedin_url": "https://linkedin.com/in/bobjones",
                "email": "bob@tech.io",
                "seniority_score": 98,
                "data_quality_score": 60,
            }
        ])

        deduped, removed = deduplicate_contacts(df)
        self.assertEqual(removed, 1)
        self.assertEqual(len(deduped), 1)
        self.assertEqual(deduped.iloc[0]["company"], "Tech Innovations")
        self.assertEqual(deduped.iloc[0]["linkedin_url"], "https://linkedin.com/in/bobjones")

    def test_distinct_people_same_name_different_companies_not_merged(self):
        """Test that two people with the same name at different companies are NOT merged."""
        df = pd.DataFrame([
            {
                "full_name": "John Doe",
                "company": "Alpha Inc",
                "position": "Director",
                "linkedin_url": "",
                "email": "",
                "seniority_score": 85,
                "data_quality_score": 40,
            },
            {
                "full_name": "John Doe",
                "company": "Beta LLC",
                "position": "Director",
                "linkedin_url": "",
                "email": "",
                "seniority_score": 85,
                "data_quality_score": 40,
            }
        ])

        deduped, removed = deduplicate_contacts(df)
        self.assertEqual(removed, 0)
        self.assertEqual(len(deduped), 2)

    def test_deduplication_by_name_and_company(self):
        """Test that records with identical name and company are merged when URL/email are absent."""
        df = pd.DataFrame([
            {
                "full_name": "Carol Danvers",
                "company": "Star Logistics",
                "position": "VP Operations",
                "linkedin_url": "",
                "email": "",
                "seniority_score": 80,
                "data_quality_score": 40,
            },
            {
                "full_name": "Carol Danvers",
                "company": "Star Logistics",
                "position": "VP Operations",
                "linkedin_url": "https://linkedin.com/in/carol-danvers",
                "email": "",
                "seniority_score": 80,
                "data_quality_score": 60,
            }
        ])

        deduped, removed = deduplicate_contacts(df)
        self.assertEqual(removed, 1)
        self.assertEqual(len(deduped), 1)
        self.assertEqual(deduped.iloc[0]["linkedin_url"], "https://linkedin.com/in/carol-danvers")


if __name__ == "__main__":
    unittest.main()
