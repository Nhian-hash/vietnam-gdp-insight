"""Unit tests for the first two V-MEST insight sections."""
from __future__ import annotations

import re
import unittest

from api.insight_config import FORBIDDEN_CAUSAL_PHRASES
from api.insights import generate_insights


class InsightRulesTests(unittest.TestCase):
    def assert_no_causal_terms(self, statements: list[str]) -> None:
        for statement in statements:
            for phrase in FORBIDDEN_CAUSAL_PHRASES:
                pattern = rf"(?<!\w){re.escape(phrase)}(?!\w)"
                self.assertIsNone(
                    re.search(pattern, statement, flags=re.IGNORECASE),
                    msg=f"Cụm nhân quả '{phrase}' xuất hiện trong: {statement}",
                )

    def test_overview_uses_ten_previous_years_and_ranks_observations(self) -> None:
        rows = [
            {"nam": year, "tang_truong_gdp_thuc_pct": float(year - 2009), "trang_thai": "uoc_tinh"}
            for year in range(2010, 2020)
        ]
        rows.append({"nam": 2020, "tang_truong_gdp_thuc_pct": 11.0, "trang_thai": "uoc_tinh"})
        data = {"growth_rows": rows, "source": "World Bank WDI"}

        statements = generate_insights("overview", data)

        self.assertEqual(len(statements), 3)
        self.assertIn("năm 2020 đạt 11,00%", statements[0])
        self.assertIn("trạng thái ước tính", statements[0])
        self.assertIn("2010–2019", statements[1])
        self.assertIn("5,50%", statements[1])
        self.assertIn("+5,50 điểm phần trăm", statements[1])
        self.assertIn("1/11", statements[2])
        self.assertIn("2010–2020", statements[2])
        self.assertTrue(all("ước tính" in statement for statement in statements))
        self.assertEqual(statements, generate_insights("overview", data))
        self.assert_no_causal_terms(statements)

    def test_overview_skips_average_when_reference_window_is_incomplete(self) -> None:
        statements = generate_insights(
            "overview",
            {
                "growth_rows": [
                    {"nam": 2019, "tang_truong_gdp_thuc_pct": 6.0},
                    {"nam": 2020, "tang_truong_gdp_thuc_pct": 7.0},
                ],
                "source": "World Bank WDI",
            },
        )

        self.assertEqual(len(statements), 2)
        self.assertFalse(any("bình quân giai đoạn" in statement for statement in statements))
        self.assert_no_causal_terms(statements)

    def test_overview_rank_counts_zero_growth_above_a_negative_latest_value(self) -> None:
        statements = generate_insights(
            "overview",
            {
                "growth_rows": [
                    {"nam": 2020, "tang_truong_gdp_thuc_pct": 0.0},
                    {"nam": 2021, "tang_truong_gdp_thuc_pct": -1.0},
                ],
                "source": "World Bank WDI",
            },
        )
        self.assertIn("xếp thứ 2/2", statements[-1])
        self.assert_no_causal_terms(statements)

    def test_overview_omits_rules_without_valid_growth_data(self) -> None:
        self.assertEqual(
            generate_insights("overview", {"growth_rows": [{"nam": 2025, "tang_truong_gdp_thuc_pct": None}]}),
            [],
        )
        self.assertEqual(generate_insights("overview", {"growth_rows": []}), [])

    def test_real_gdp_and_sector_share_keep_units_periods_and_statuses(self) -> None:
        data = {
            "real_rows": [
                {"nam": 2020, "gdp_thuc_usd_2015": 100_000_000_000.0},
                {"nam": 2025, "gdp_thuc_usd_2015": 125_000_000_000.0},
            ],
            "real_source": "World Bank WDI",
            "sector_rows": [
                {
                    "nam": 2020,
                    "ty_trong_nong_lam_thuy_san_pct": 12.0,
                    "ty_trong_cong_nghiep_xay_dung_pct": 35.0,
                    "ty_trong_dich_vu_pct": 40.0,
                    "trang_thai": "chinh_thuc_theo_bang_nguon",
                },
                {
                    "nam": 2025,
                    "ty_trong_nong_lam_thuy_san_pct": 11.0,
                    "ty_trong_cong_nghiep_xay_dung_pct": 38.0,
                    "ty_trong_dich_vu_pct": 43.0,
                    "trang_thai": "uoc_tinh",
                },
            ],
            "sector_source": "NSO/GSO",
        }

        statements = generate_insights("gdp-real-structure", data)

        self.assertEqual(len(statements), 2)
        self.assertIn("năm 2025 đạt 125,00 tỷ USD", statements[0])
        self.assertIn("nguồn World Bank WDI", statements[0])
        self.assertIn("năm 2025", statements[1])
        self.assertIn("dịch vụ (43,00%)", statements[1])
        self.assertIn("năm 2020 là +3,00 điểm phần trăm", statements[1])
        self.assertIn("năm 2020 chính thức theo bảng nguồn", statements[1])
        self.assertIn("năm 2025 ước tính", statements[1])
        self.assertEqual(statements, generate_insights("gdp-real-structure", data))
        self.assert_no_causal_terms(statements)

    def test_missing_structure_rows_leave_only_available_sentence(self) -> None:
        statements = generate_insights(
            "gdp-real-structure",
            {"real_rows": [{"nam": 2025, "gdp_thuc_usd_2015": 125_000_000_000.0}]},
        )
        self.assertEqual(len(statements), 1)
        self.assertIn("2025", statements[0])
        self.assertFalse(any("Cơ cấu GDP" in statement for statement in statements))
        self.assert_no_causal_terms(statements)

    def test_empty_structure_data_generates_no_claims(self) -> None:
        self.assertEqual(generate_insights("gdp-real-structure", {}), [])

    def test_unknown_section_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            generate_insights("not-a-section", {})


if __name__ == "__main__":
    unittest.main()
