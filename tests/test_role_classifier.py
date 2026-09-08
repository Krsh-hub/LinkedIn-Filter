"""Unit tests for role classification and matching."""

import unittest
from src.role_classifier import classify_role, matches_role_filter, normalize_title


class TestRoleClassifier(unittest.TestCase):
    """Test suite for role classifier rules, combinations, and boundaries."""

    def test_founder_detection(self):
        """Test detection of founder titles."""
        prim, sec = classify_role("Founder")
        self.assertEqual(prim, "Founder")

        prim2, _ = classify_role("Founding Partner")
        self.assertEqual(prim2, "Founder")

    def test_co_founder_detection(self):
        """Test detection of co-founder titles with variations."""
        for title in ["Co-Founder", "Cofounder", "Co Founder"]:
            prim, _ = classify_role(title)
            self.assertEqual(prim, "Founder", f"Failed for title: {title}")

    def test_ceo_detection(self):
        """Test CEO detection both acronym and full title."""
        prim, _ = classify_role("CEO")
        self.assertEqual(prim, "CEO")

        prim2, _ = classify_role("Chief Executive Officer")
        self.assertEqual(prim2, "CEO")

    def test_cto_detection(self):
        """Test CTO detection both acronym and full title."""
        prim, _ = classify_role("CTO")
        self.assertEqual(prim, "CTO")

        prim2, _ = classify_role("Chief Technology Officer")
        self.assertEqual(prim2, "CTO")

    def test_director_detection(self):
        """Test Director detection for standard and executive variants."""
        prim, _ = classify_role("Director")
        self.assertEqual(prim, "Director")

        prim_md, _ = classify_role("Managing Director")
        self.assertEqual(prim_md, "Director")

        prim_ed, _ = classify_role("Executive Director")
        self.assertEqual(prim_ed, "Director")

    def test_founder_and_ceo_combination(self):
        """Test combined 'Founder & CEO' produces primary=Founder, secondary=['CEO']."""
        prim, sec = classify_role("Founder & CEO")
        self.assertEqual(prim, "Founder")
        self.assertIn("CEO", sec)

        prim_cofounder, sec_cofounder = classify_role("Co-Founder & CEO")
        self.assertEqual(prim_cofounder, "Founder")
        self.assertIn("CEO", sec_cofounder)

    def test_founder_and_cto_combination(self):
        """Test combined 'Founder & CTO' produces primary=Founder, secondary=['CTO']."""
        prim, sec = classify_role("Founder & CTO")
        self.assertEqual(prim, "Founder")
        self.assertIn("CTO", sec)

        prim_co, sec_co = classify_role("Co-Founder & CTO")
        self.assertEqual(prim_co, "Founder")
        self.assertIn("CTO", sec_co)

    def test_case_insensitive_matching(self):
        """Test that title matching is strictly case-insensitive."""
        prim, sec = classify_role("founder & cto")
        self.assertEqual(prim, "Founder")
        self.assertIn("CTO", sec)

        prim_upper, _ = classify_role("CHIEF TECHNOLOGY OFFICER")
        self.assertEqual(prim_upper, "CTO")

    def test_word_boundary_avoids_false_positives(self):
        """Test that substring words do NOT trigger false matches (e.g. receptionist != CEO)."""
        prim, sec = classify_role("Receptionist")
        self.assertEqual(prim, "Other")
        self.assertEqual(sec, [])

        prim2, _ = classify_role("Soccer player Conceicao")
        self.assertEqual(prim2, "Other")

        prim3, _ = classify_role("Senior Associate")
        self.assertEqual(prim3, "Other")

    def test_empty_positions(self):
        """Test handling of empty, whitespace, and None positions."""
        self.assertEqual(classify_role(""), ("Other", []))
        self.assertEqual(classify_role("   "), ("Other", []))
        self.assertEqual(classify_role(None), ("Other", []))

    def test_entrepreneurs(self):
        """Test detection of entrepreneur and owner titles."""
        prim, _ = classify_role("Entrepreneur")
        self.assertEqual(prim, "Entrepreneur")

        prim2, _ = classify_role("Business Owner")
        self.assertEqual(prim2, "Entrepreneur")

    def test_role_filtering(self):
        """Test matches_role_filter logic for various filters."""
        # Founder filter
        self.assertTrue(matches_role_filter("founder", "Founder", ["CEO"], "Founder"))
        self.assertFalse(matches_role_filter("founder", "Director", [], "Director"))

        # CTO filter
        self.assertTrue(matches_role_filter("cto", "Founder", ["CTO"], "Founder"))
        self.assertTrue(matches_role_filter("cto", "CTO", [], "C-Suite"))
        self.assertFalse(matches_role_filter("cto", "CEO", [], "C-Suite"))

        # C-Suite filter
        self.assertTrue(matches_role_filter("c-suite", "CEO", [], "C-Suite"))
        self.assertTrue(matches_role_filter("c-suite", "CTO", [], "C-Suite"))
        self.assertTrue(matches_role_filter("c-suite", "Founder", ["CEO"], "Founder"))

        # Director filter
        self.assertTrue(matches_role_filter("director", "Director", [], "Director"))


if __name__ == "__main__":
    unittest.main()
