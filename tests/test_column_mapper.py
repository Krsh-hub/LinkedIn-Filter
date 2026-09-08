"""Unit tests for column mapping and detection."""

import unittest
import pandas as pd
from src.column_mapper import identify_columns, map_and_normalize_dataframe


class TestColumnMapper(unittest.TestCase):
    """Test suite for intelligent column detection and dataframe normalization."""

    def test_standard_linkedin_headers(self):
        """Test recognition of standard LinkedIn exported CSV columns."""
        headers = ["First Name", "Last Name", "URL", "Email Address", "Company", "Position", "Connected On"]
        schema_map, display_map = identify_columns(headers)

        self.assertEqual(schema_map["first_name"], "First Name")
        self.assertEqual(schema_map["last_name"], "Last Name")
        self.assertEqual(schema_map["linkedin_url"], "URL")
        self.assertEqual(schema_map["email"], "Email Address")
        self.assertEqual(schema_map["company"], "Company")
        self.assertEqual(schema_map["position"], "Position")
        self.assertEqual(schema_map["connected_on"], "Connected On")
        self.assertIn("First Name + Last Name", display_map["Name"])

    def test_alternative_header_variations(self):
        """Test recognition of common variations in column headers."""
        headers = ["Firstname", "Lastname", "Profile Link", "E-mail", "Organization", "Job Title"]
        schema_map, _ = identify_columns(headers)

        self.assertEqual(schema_map["first_name"], "Firstname")
        self.assertEqual(schema_map["last_name"], "Lastname")
        self.assertEqual(schema_map["linkedin_url"], "Profile Link")
        self.assertEqual(schema_map["email"], "E-mail")
        self.assertEqual(schema_map["company"], "Organization")
        self.assertEqual(schema_map["position"], "Job Title")

    def test_full_name_synthesis(self):
        """Test synthesis of full_name from first and last names."""
        df = pd.DataFrame([
            {"First Name": "Satya", "Last Name": "Nadella", "Company": "Microsoft", "Position": "CEO"}
        ])
        mapped_df, _ = map_and_normalize_dataframe(df)

        self.assertEqual(mapped_df.loc[0, "full_name"], "Satya Nadella")
        self.assertEqual(mapped_df.loc[0, "first_name"], "Satya")
        self.assertEqual(mapped_df.loc[0, "last_name"], "Nadella")
        self.assertEqual(mapped_df.loc[0, "company"], "Microsoft")
        self.assertEqual(mapped_df.loc[0, "position"], "CEO")

    def test_missing_columns_graceful_handling(self):
        """Test that missing columns result in empty strings rather than exceptions."""
        df = pd.DataFrame([
            {"Name": "Alan Turing", "Company": "Bletchley Park"}
        ])
        mapped_df, _ = map_and_normalize_dataframe(df)

        self.assertEqual(mapped_df.loc[0, "full_name"], "Alan Turing")
        self.assertEqual(mapped_df.loc[0, "position"], "")
        self.assertEqual(mapped_df.loc[0, "email"], "")
        self.assertEqual(mapped_df.loc[0, "linkedin_url"], "")
        self.assertEqual(mapped_df.loc[0, "connected_on"], "")

    def test_location_column_detection(self):
        """Test detection of optional location column when present."""
        df = pd.DataFrame([
            {"First Name": "Sundar", "Last Name": "Pichai", "Location": "Mountain View, CA"}
        ])
        mapped_df, display_map = map_and_normalize_dataframe(df)

        self.assertEqual(mapped_df.loc[0, "location"], "Mountain View, CA")
        self.assertEqual(display_map.get("Location"), "Location")


if __name__ == "__main__":
    unittest.main()
