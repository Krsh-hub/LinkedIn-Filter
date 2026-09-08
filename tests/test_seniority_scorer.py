"""Unit tests for seniority scoring, level mapping, and lead type assignment."""

import unittest
from src.seniority_scorer import (
    assign_lead_type,
    assign_seniority_level,
    calculate_seniority_score,
)


class TestSeniorityScorer(unittest.TestCase):
    """Test suite for seniority scores, levels, and lead types."""

    def test_individual_role_scores(self):
        """Test specific baseline score rules from prompt."""
        self.assertEqual(calculate_seniority_score("Founder"), 100)
        self.assertEqual(calculate_seniority_score("Co-Founder"), 100)
        self.assertEqual(calculate_seniority_score("CEO"), 98)
        self.assertEqual(calculate_seniority_score("Chief Executive Officer"), 98)
        self.assertEqual(calculate_seniority_score("CTO"), 98)
        self.assertEqual(calculate_seniority_score("Chief Technology Officer"), 98)
        self.assertEqual(calculate_seniority_score("CFO"), 95)
        self.assertEqual(calculate_seniority_score("COO"), 95)
        self.assertEqual(calculate_seniority_score("CMO"), 93)
        self.assertEqual(calculate_seniority_score("CIO"), 93)
        self.assertEqual(calculate_seniority_score("Managing Director"), 92)
        self.assertEqual(calculate_seniority_score("Executive Director"), 90)
        self.assertEqual(calculate_seniority_score("Director"), 85)
        self.assertEqual(calculate_seniority_score("Partner"), 85)
        self.assertEqual(calculate_seniority_score("President"), 85)
        self.assertEqual(calculate_seniority_score("Senior Vice President"), 82)
        self.assertEqual(calculate_seniority_score("VP of Product"), 80)
        self.assertEqual(calculate_seniority_score("Head of AI"), 75)
        self.assertEqual(calculate_seniority_score("Entrepreneur"), 70)

    def test_multiple_senior_roles_highest_score(self):
        """Test that the highest score wins when multiple senior roles are present."""
        # Founder (100) & CEO (98) -> 100
        self.assertEqual(calculate_seniority_score("Founder & CEO"), 100)
        # Co-Founder (100) & CTO (98) -> 100
        self.assertEqual(calculate_seniority_score("Co-Founder & CTO"), 100)
        # VP (80) & Head of AI (75) -> 80
        self.assertEqual(calculate_seniority_score("VP & Head of AI"), 80)

    def test_non_senior_roles(self):
        """Test non-senior positions return score 0."""
        self.assertEqual(calculate_seniority_score("Software Engineer"), 0)
        self.assertEqual(calculate_seniority_score("Student Intern"), 0)
        self.assertEqual(calculate_seniority_score("Administrative Assistant"), 0)

    def test_seniority_level_mapping(self):
        """Test mapping to seniority_level values."""
        self.assertEqual(assign_seniority_level("Founder", "Founder & CEO", 100), "Founder")
        self.assertEqual(assign_seniority_level("CEO", "Chief Executive Officer", 98), "C-Suite")
        self.assertEqual(assign_seniority_level("CTO", "CTO", 98), "C-Suite")
        self.assertEqual(assign_seniority_level("Director", "Managing Director", 92), "Executive")
        self.assertEqual(assign_seniority_level("Director", "Director", 85), "Executive")
        self.assertEqual(assign_seniority_level("VP", "VP of Engineering", 80), "Senior Leadership")
        self.assertEqual(assign_seniority_level("Entrepreneur", "Business Owner", 70), "Entrepreneur")
        self.assertEqual(assign_seniority_level("Other", "Analyst", 0), "Other")

    def test_lead_type_mapping(self):
        """Test assignment of lead_type."""
        self.assertEqual(assign_lead_type("Founder", 100), "Founder")
        self.assertEqual(assign_lead_type("CEO", 98), "C-Suite")
        self.assertEqual(assign_lead_type("CTO", 98), "C-Suite")
        self.assertEqual(assign_lead_type("Director", 85), "Director")
        self.assertEqual(assign_lead_type("VP", 80), "Senior Leadership")
        self.assertEqual(assign_lead_type("Entrepreneur", 70), "Entrepreneur")
        self.assertEqual(assign_lead_type("Other", 0), "Other")


if __name__ == "__main__":
    unittest.main()
