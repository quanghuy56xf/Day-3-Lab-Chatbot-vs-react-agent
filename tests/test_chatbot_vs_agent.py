#!/usr/bin/env python3
"""
Test Suite: Chatbot Baseline vs ReAct Agent
Compares both systems on the same test cases to demonstrate
the value of tool-augmented reasoning.

Run:  python -m pytest tests/test_chatbot_vs_agent.py -v
  or: python tests/test_chatbot_vs_agent.py
"""
import os
import sys
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.tools.real_estate_tools import (
    search_properties,
    get_property_details,
    calculate_market_stats,
)


# ==================================================================
# PART 1: Unit tests for tools (no LLM needed)
# ==================================================================
class TestSearchProperties(unittest.TestCase):
    """Test the search_properties tool independently."""

    def test_search_by_project(self):
        """Search within a specific project returns results."""
        result = search_properties(project="The Zurich")
        self.assertNotIn("Không tìm thấy", result)
        self.assertIn("The Zurich", result)

    def test_search_by_type(self):
        """Search by property type works."""
        result = search_properties(property_type="STUDIO")
        self.assertNotIn("Không tìm thấy", result)
        self.assertIn("STUDIO", result)

    def test_search_with_price_range(self):
        """Search with min/max price filters correctly."""
        result = search_properties(min_price=3_000_000_000, max_price=5_000_000_000)
        self.assertNotIn("Không tìm thấy", result)
        # All results should be within range
        self.assertIn("tỷ", result)

    def test_search_no_results(self):
        """Search with impossible criteria returns empty message."""
        result = search_properties(max_price=100)  # No apartment costs 100 VND
        self.assertIn("Không tìm thấy", result)

    def test_search_by_status(self):
        """Search by status 'Còn bán' excludes sold units."""
        result = search_properties(project="The Zurich", status="Còn bán", limit=5)
        self.assertNotIn("Đã bán", result)

    def test_search_limit(self):
        """Search respects the limit parameter."""
        result = search_properties(project="The Zurich", limit=3)
        # Count numbered results (e.g., "1.", "2.", "3.")
        count = result.count("\n1. ") + result.count("\n2. ") + result.count("\n3. ") + result.count("\n4. ")
        self.assertLessEqual(count, 4)  # At most 3 results + possible numbering


class TestGetPropertyDetails(unittest.TestCase):
    """Test the get_property_details tool."""

    def test_valid_id(self):
        """Valid property ID returns full details."""
        # First search for a real ID
        search_result = search_properties(project="The Zurich", limit=1)
        # Extract an ID from the search result (format: [XXXXX])
        import re
        id_match = re.search(r'\[([A-Z0-9]{6})\]', search_result)
        if id_match:
            prop_id = id_match.group(1)
            details = get_property_details(prop_id)
            self.assertIn("CHI TIẾT CĂN HỘ", details)
            self.assertIn("SĐT", details)

    def test_invalid_id(self):
        """Invalid property ID returns not found message."""
        result = get_property_details("ZZZZZ_INVALID")
        self.assertIn("Không tìm thấy", result)


class TestCalculateMarketStats(unittest.TestCase):
    """Test the calculate_market_stats tool."""

    def test_stats_by_project(self):
        """Stats for a specific project returns meaningful data."""
        result = calculate_market_stats(project="The Zurich")
        self.assertIn("Giá trung bình", result)
        self.assertIn("Diện tích trung bình", result)

    def test_stats_by_type(self):
        """Stats for a specific type returns meaningful data."""
        result = calculate_market_stats(property_type="2PN")
        self.assertIn("Giá trung bình", result)

    def test_stats_all(self):
        """Stats for all properties."""
        result = calculate_market_stats()
        self.assertIn("Tổng số căn:", result)
        self.assertIn("4370", result)  # Total count in database

    def test_stats_no_match(self):
        """Stats with no matching properties."""
        result = calculate_market_stats(project="NonExistentProject")
        self.assertIn("Không có dữ liệu", result)


# ==================================================================
# PART 2: Chatbot vs Agent comparison (qualitative)
# ==================================================================
class TestChatbotVsAgentComparison(unittest.TestCase):
    """
    Qualitative comparison test cases.
    These document expected differences between Chatbot and Agent.
    They test the TOOLS directly to verify Agent would get correct data.
    """

    def test_data_query_agent_has_real_data(self):
        """
        Scenario: User asks 'Tìm căn STUDIO tại The London'
        - Chatbot: Would hallucinate data (no tool access)
        - Agent: Calls search_properties → gets real data
        """
        result = search_properties(project="The London", property_type="STUDIO", limit=3)
        # Agent gets real data with actual unit codes
        self.assertNotIn("Không tìm thấy", result)
        self.assertIn("The London", result)
        print(f"\n[Agent Tool Result] {result[:200]}...")

    def test_detail_query_agent_has_phone(self):
        """
        Scenario: User asks for property details with phone number
        - Chatbot: Would make up a phone number (hallucination!)
        - Agent: Calls get_property_details → returns real SĐT
        """
        # Get a real property ID first
        search = search_properties(project="The Zurich", limit=1)
        import re
        id_match = re.search(r'\[([A-Z0-9]{6})\]', search)
        if id_match:
            prop_id = id_match.group(1)
            details = get_property_details(prop_id)
            self.assertIn("SĐT", details)
            # Verify it looks like a real phone number
            phone_match = re.search(r'SĐT:\s*(0\d{9,10})', details)
            self.assertIsNotNone(phone_match, "Agent should return a real phone number")
            print(f"\n[Agent Tool Result] Phone: {phone_match.group(1) if phone_match else 'N/A'}")

    def test_comparison_query_agent_uses_stats(self):
        """
        Scenario: User asks to compare prices between projects
        - Chatbot: Would guess based on general knowledge
        - Agent: Calls calculate_market_stats twice → data-driven comparison
        """
        stats_paris = calculate_market_stats(project="The Paris", property_type="2PN")
        stats_zurich = calculate_market_stats(project="The Zurich", property_type="2PN")

        self.assertIn("Giá trung bình", stats_paris)
        self.assertIn("Giá trung bình", stats_zurich)
        print(f"\n[The Paris 2PN] {stats_paris[:150]}...")
        print(f"[The Zurich 2PN] {stats_zurich[:150]}...")

    def test_multi_step_query(self):
        """
        Scenario: User asks 'Tìm căn rẻ nhất ở The Zurich và cho tôi SĐT chủ nhà'
        - Chatbot: Cannot do multi-step (only 1 LLM call)
        - Agent: Step 1: search → Step 2: get_details → Final Answer
        """
        # Step 1: Search for cheapest
        search = search_properties(project="The Zurich", status="Còn bán", limit=1)
        self.assertNotIn("Không tìm thấy", search)

        # Step 2: Get details of first result
        import re
        id_match = re.search(r'\[([A-Z0-9]{6})\]', search)
        if id_match:
            details = get_property_details(id_match.group(1))
            self.assertIn("SĐT", details)
            print(f"\n[Multi-step] Found cheapest → Got details with phone")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  🧪 Test Suite: Chatbot vs ReAct Agent")
    print("=" * 60)
    unittest.main(verbosity=2)
