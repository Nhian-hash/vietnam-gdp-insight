"""Unit tests for deterministic V-MEST insight rules."""
from __future__ import annotations

import re
import unittest

from api.insight_config import FORBIDDEN_CAUSAL_PHRASES
from api.insights import format_vi, generate_insights


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


    def test_macro_insights_report_cpi_peak_and_monthly_exchange_rate(self) -> None:
        data = {
            "cpi_source": "NSO",
            "cpi_rows": [
                {
                    "thoi_gian": "2026-08-01",
                    "cpi_thay_doi_cung_ky_pct": 4.89,
                    "cpi_binh_quan_luy_ke_yoy_pct": 4.45,
                    "ngay_cong_bo": "2026-09-03",
                    "trang_thai": "cong_bo_chinh_thuc_nso",
                },
                {
                    "thoi_gian": "2026-09-01",
                    "cpi_thay_doi_cung_ky_pct": 5.08,
                    "cpi_binh_quan_luy_ke_yoy_pct": 4.52,
                    "ngay_cong_bo": "2026-10-03",
                    "trang_thai": "cong_bo_chinh_thuc_nso",
                },
            ],
            "fx_source": "IMF IFS",
            "fx_rows": [
                {
                    "thoi_gian": "2026-07-01",
                    "ty_gia_usd_vnd": 25246.96,
                    "loai_ty_gia": "binh_quan_ky",
                    "trang_thai": "IMF_observed",
                },
                {
                    "thoi_gian": "2026-08-01",
                    "ty_gia_usd_vnd": 25534.42,
                    "loai_ty_gia": "binh_quan_ky",
                    "trang_thai": "IMF_observed",
                },
            ],
        }

        statements = generate_insights("macro", data)

        self.assertEqual(len(statements), 4)
        self.assertIn("đến tháng 09/2026 tăng 4,52%", statements[0])
        self.assertIn("CPI tháng 09/2026 tăng 5,08%", statements[1])
        self.assertIn("từ 08/2026 đến 09/2026, mức cao nhất là 5,08%", statements[2])
        self.assertIn("đạt 25.534,42 VND/USD tháng 08/2026", statements[3])
        self.assertIn("+287,46 VND/USD (+1,14%) so với tháng 07/2026", statements[3])
        self.assertTrue(all("công bố chính thức NSO" in item or "quan sát IMF" in item for item in statements))
        self.assertEqual(statements, generate_insights("macro", data))
        self.assert_no_causal_terms(statements)

    def test_macro_omits_missing_metrics(self) -> None:
        self.assertEqual(
            generate_insights("macro", {"cpi_rows": [], "fx_rows": []}),
            [],
        )
        statements = generate_insights(
            "macro",
            {
                "cpi_rows": [{"thoi_gian": "2026-10-01", "cpi_thay_doi_cung_ky_pct": None}],
                "fx_rows": [{"thoi_gian": "2026-08-01", "ty_gia_usd_vnd": 25534.42}],
            },
        )
        self.assertEqual(len(statements), 1)
        self.assertIn("tháng 08/2026", statements[0])
        self.assert_no_causal_terms(statements)

    def test_growth_drivers_select_largest_positive_and_negative_components(self) -> None:
        data = {
            "source": "NSO",
            "contribution_rows": [
                {
                    "nam": 2025,
                    "tang_truong_gdp_thuc_chi_tieu_pct": 8.02,
                    "trang_thai": "uoc_tinh",
                    "dong_gop_von_co_dinh_diem_pct": 2.95,
                    "dong_gop_ton_kho_diem_pct": 0.18,
                    "dong_gop_tieu_dung_nha_nuoc_diem_pct": 1.06,
                    "dong_gop_tieu_dung_ho_gia_dinh_diem_pct": 3.99,
                    "dong_gop_can_can_hang_hoa_dich_vu_diem_pct": -0.59,
                    "dong_gop_chenh_lech_thong_ke_diem_pct": 0.43,
                }
            ],
        }

        statements = generate_insights("growth-drivers", data)

        self.assertEqual(len(statements), 2)
        self.assertIn("năm 2025 đạt 8,02%", statements[0])
        self.assertIn("trạng thái ước tính", statements[0])
        self.assertIn("tiêu dùng hộ gia đình (+3,99 điểm phần trăm)", statements[1])
        self.assertIn("cán cân hàng hóa và dịch vụ (-0,59 điểm phần trăm)", statements[1])
        self.assertIn("nguồn NSO", statements[1])
        self.assertEqual(statements, generate_insights("growth-drivers", data))
        self.assert_no_causal_terms(statements)

    def test_growth_drivers_omit_missing_contributions(self) -> None:
        statements = generate_insights(
            "growth-drivers",
            {
                "contribution_rows": [
                    {
                        "nam": 2025,
                        "tang_truong_gdp_thuc_chi_tieu_pct": 8.02,
                        "trang_thai": "uoc_tinh",
                    }
                ]
            },
        )
        self.assertEqual(len(statements), 1)
        self.assertIn("8,02%", statements[0])
        self.assert_no_causal_terms(statements)


    def test_trade_and_iip_use_latest_period_source_units_and_status(self) -> None:
        data = {
            "trade_source": "NSO",
            "trade_rows": [
                {
                    "thoi_gian": "2026-08-01",
                    "kim_ngach_xuat_khau_usd": 54_776_335_197,
                    "kim_ngach_nhap_khau_usd": 55_117_743_547,
                    "can_can_thuong_mai_usd": -341_408_350,
                    "trang_thai": "so_bo",
                },
                {
                    "thoi_gian": "2026-09-01",
                    "kim_ngach_xuat_khau_usd": 59_506_115_885,
                    "kim_ngach_nhap_khau_usd": 58_206_560_939,
                    "can_can_thuong_mai_usd": 1_299_554_946,
                    "trang_thai": "so_bo",
                },
            ],
            "iip_source": "NSO",
            "iip_rows": [
                {
                    "thoi_gian": "2026-09-01",
                    "chi_so_iip_toan_nganh_2015_100": 223.99,
                    "tang_truong_mom_pct": 3.26,
                    "tang_truong_yoy_pct": 16.65,
                    "trang_thai": "so_bo",
                }
            ],
        }

        statements = generate_insights("trade", data)

        self.assertEqual(len(statements), 2)
        self.assertIn("Tháng 09/2026, xuất khẩu 59,51 tỷ USD", statements[0])
        self.assertIn("nhập khẩu 58,21 tỷ USD", statements[0])
        self.assertIn("thặng dư thương mại 1,30 tỷ USD", statements[0])
        self.assertIn("trạng thái sơ bộ; nguồn NSO", statements[0])
        self.assertIn("223,99 điểm (2015=100)", statements[1])
        self.assertIn("so với tháng trước +3,26%", statements[1])
        self.assertIn("so với cùng kỳ +16,65%", statements[1])
        self.assertEqual(statements, generate_insights("trade", data))
        self.assert_no_causal_terms(statements)

    def test_trade_omits_rows_with_missing_values(self) -> None:
        self.assertEqual(generate_insights("trade", {"trade_rows": [], "iip_rows": []}), [])
        statements = generate_insights(
            "trade",
            {
                "trade_rows": [{"thoi_gian": "2026-09-01", "trang_thai": "so_bo"}],
                "iip_rows": [
                    {
                        "thoi_gian": "2026-09-01",
                        "chi_so_iip_toan_nganh_2015_100": None,
                    }
                ],
            },
        )
        self.assertEqual(statements, [])


    def test_sector_sections_report_ytd_quarter_and_top_subsector(self) -> None:
        broad = {
            "agriculture": ("Nông, lâm, thủy sản", 4.02, 5.35, 10.65, 4.21, 5.14),
            "industry": ("Công nghiệp và xây dựng", 11.21, 49.62, 38.35, 12.50, 51.57),
            "services": ("Dịch vụ", 8.69, 45.03, 42.97, 9.54, 43.29),
        }
        subsectors = {
            "agriculture": [("Nông nghiệp", 3.72), ("Lâm nghiệp", 3.99), ("Thủy sản", 4.99)],
            "industry": [("Công nghiệp", 11.02), ("Công nghiệp chế biến, chế tạo", 11.36), ("Xây dựng", 12.22)],
            "services": [
                ("Vận tải, kho bãi", 11.03),
                ("Bán buôn và bán lẻ", 9.85),
                ("Tài chính, ngân hàng và bảo hiểm", 9.45),
                ("Lưu trú và ăn uống", 8.83),
            ],
        }
        rows: list[dict[str, object]] = []
        for section, (label, ytd_growth, contribution, gdp_share, q3_growth, q3_contribution) in broad.items():
            rows.extend(
                [
                    {
                        "ky": "2026-9M",
                        "ky_hien_thi": "9 tháng/2026",
                        "khu_vuc_ma": section,
                        "hoat_dong_kinh_te": label,
                        "tang_truong_gdp_thuc_yoy_pct": ytd_growth,
                        "ty_trong_dong_gop_tang_truong_pct": contribution,
                        "ty_trong_gdp_9_thang_pct": gdp_share,
                        "cap_phan_tich": "9m_broad",
                        "trang_thai": "uoc_tinh",
                    },
                    {
                        "ky": "2026-Q3",
                        "ky_hien_thi": "Quý III/2026",
                        "khu_vuc_ma": section,
                        "hoat_dong_kinh_te": label,
                        "tang_truong_gdp_thuc_yoy_pct": q3_growth,
                        "ty_trong_dong_gop_tang_truong_pct": q3_contribution,
                        "cap_phan_tich": "q3_broad",
                        "trang_thai": "uoc_tinh",
                    },
                ]
            )
            rows.extend(
                {
                    "ky": "2026-9M",
                    "ky_hien_thi": "9 tháng/2026",
                    "khu_vuc_ma": section,
                    "hoat_dong_kinh_te": activity,
                    "tang_truong_gdp_thuc_yoy_pct": growth,
                    "cap_phan_tich": "9m_subsector",
                    "trang_thai": "uoc_tinh",
                }
                for activity, growth in subsectors[section]
            )

        for section, (label, ytd_growth, contribution, gdp_share, q3_growth, q3_contribution) in broad.items():
            with self.subTest(section=section):
                statements = generate_insights(
                    section,
                    {"sector_rows": rows, "source": "NSO/GSO"},
                )
                top_activity, top_growth = max(subsectors[section], key=lambda pair: pair[1])
                self.assertEqual(len(statements), 3)
                self.assertIn("9 tháng/2026", statements[0])
                self.assertIn(f"tăng {format_vi(ytd_growth)}%", statements[0])
                self.assertIn(f"tỷ trọng GDP là {format_vi(gdp_share)}%", statements[0])
                self.assertIn(top_activity, statements[1])
                self.assertIn(f"{format_vi(top_growth)}%", statements[1])
                self.assertIn("Quý III/2026", statements[2])
                self.assertIn(f"{format_vi(q3_growth)}%", statements[2])
                self.assertTrue(all("trạng thái ước tính" in item for item in statements))
                self.assertTrue(all("nguồn NSO/GSO" in item for item in statements))
                self.assertEqual(statements, generate_insights(section, {"sector_rows": rows, "source": "NSO/GSO"}))
                self.assert_no_causal_terms(statements)

    def test_sector_rules_omit_missing_subsector_and_share_claims(self) -> None:
        statements = generate_insights(
            "agriculture",
            {
                "sector_rows": [
                    {
                        "ky": "2026-9M",
                        "ky_hien_thi": "9 tháng/2026",
                        "khu_vuc_ma": "agriculture",
                        "tang_truong_gdp_thuc_yoy_pct": 4.02,
                        "cap_phan_tich": "9m_broad",
                        "trang_thai": "uoc_tinh",
                    }
                ]
            },
        )
        self.assertEqual(len(statements), 1)
        self.assertIn("4,02%", statements[0])
        self.assertNotIn("tỷ trọng GDP", statements[0])
        self.assertFalse(any("phân ngành" in item for item in statements))
        self.assert_no_causal_terms(statements)
        self.assertEqual(generate_insights("industry", {"sector_rows": []}), [])
        self.assertEqual(generate_insights("services", {}), [])


if __name__ == "__main__":
    unittest.main()
