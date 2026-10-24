
import math
import os
import tempfile
import unittest
from types import SimpleNamespace

import matplotlib

matplotlib.use("Agg")

import generate_data as gd
import weather_mis as wm  

NAN = math.nan


def make_records(pm25_values):

    records = []
    for index in range(len(pm25_values)):
        records.append({"date": "2025-01-%02d" % (index + 1), "year": 2025, "month": 1,
                        "day": index + 1, "temperature": 27.0, "humidity": 70.0,
                        "rainfall": 0.0, "pm25": pm25_values[index], "pm10": 60.0,
                        "no2": 20.0})
    return records


class StatisticsTests(unittest.TestCase):
 

    def test_normal_values(self):
        stats = wm.compute_stats([20, 35, 50, 62, 30])
        self.assertEqual(stats["count"], 5)
        self.assertEqual(stats["min"], 20)
        self.assertEqual(stats["max"], 62)
        self.assertAlmostEqual(stats["mean"], 39.4)

    def test_empty_value_is_skipped(self):
        stats = wm.compute_stats([10, NAN, 40, None, 25])
        self.assertEqual(stats["count"], 3)
        self.assertAlmostEqual(stats["mean"], 25)

    def test_all_empty(self):
        stats = wm.compute_stats([NAN, None])
        self.assertEqual(stats["count"], 0)
        self.assertTrue(math.isnan(stats["mean"]))

    def test_negative_values(self):
        self.assertEqual(wm.compute_stats([-3, -1])["min"], -3)

    def test_labels_of_min_and_max(self):
        stats = wm.compute_stats([5, 1, 9], [11, 12, 13])
        self.assertEqual(stats["min_label"], 12)
        self.assertEqual(stats["max_label"], 13)


class AlertTests(unittest.TestCase):


    def test_value_equal_to_limit_is_not_an_alert(self):
        alerts = wm.find_alerts(make_records([49.9, 50.0, 50.1]), {"pm25": 50})
        self.assertEqual(len(alerts), 1)
        self.assertAlmostEqual(alerts[0].value, 50.1)

    def test_severity_levels(self):
        def level(value):
            return wm.Alert("2025-01-01", "pm25", value, 50).severity()
        self.assertEqual(level(55), "WARNING")
        self.assertEqual(level(75), "HIGH")
        self.assertEqual(level(100), "CRITICAL")

    def test_empty_value_gives_no_alert(self):
        self.assertEqual(wm.find_alerts(make_records([NAN, None]), {"pm25": 50}), [])

    def test_count_days_above(self):
        records = make_records([10, 20, 30, NAN])
        self.assertEqual(wm.count_days_above(records, "pm25", 15), 2)


class ClassifyTests(unittest.TestCase):


    def test_results(self):
        self.assertEqual(wm.classify(20, 25), "Compliant")
        self.assertEqual(wm.classify(25, 25), "Compliant")
        self.assertEqual(wm.classify(26, 25), "Non-compliant")
        self.assertEqual(wm.classify(NAN, 25), "No data")


class GeneratedDataTests(unittest.TestCase):


    @classmethod
    def setUpClass(cls):
        cls.rows = gd.generate_rows()

    def test_number_of_days_and_columns(self):
        self.assertEqual(len(self.rows), 731)          # 2024 is a leap year: 366 + 365
        for name in gd.COLUMNS:
            self.assertIn(name, self.rows[0])

    def test_same_seed_gives_same_data(self):
        self.assertEqual(gd.generate_rows(7), gd.generate_rows(7))

    def test_values_are_logical(self):
        for row in self.rows:
            if row["pm25"] != "" and row["pm10"] != "":
                self.assertGreater(row["pm10"], row["pm25"])    # PM10 includes PM2.5
            if row["humidity"] != "":
                self.assertTrue(40 <= row["humidity"] <= 100)
            if row["rainfall"] != "":
                self.assertGreaterEqual(row["rainfall"], 0)

    def test_rainy_season_is_wetter_than_dry_season(self):
        def rain_of(month):
            total = 0.0
            for row in self.rows:
                if int(row["date"][5:7]) == month and row["rainfall"] != "":
                    total = total + row["rainfall"]
            return total
        self.assertGreater(rain_of(9), 5 * rain_of(2))

    def test_some_values_are_missing(self):
        empty = sum(1 for row in self.rows for name in gd.COLUMNS[1:] if row[name] == "")
        self.assertGreater(empty, 0)


class ReadingTests(unittest.TestCase):


    def test_to_number(self):
        self.assertEqual(wm.to_number("12.5"), 12.5)
        self.assertIsNone(wm.to_number(""))
        self.assertIsNone(wm.to_number("abc"))

    def test_read_data(self):
        records = wm.read_data()
        self.assertEqual(len(records), 731)
        self.assertEqual(len(wm.list_months(records)), 24)

    def test_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            wm.read_data("no_such_file.csv")

    def test_missing_column(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "bad.csv")
            with open(path, "w", encoding="utf-8") as file:
                file.write("date,temperature\n2025-01-01,27\n")
            with self.assertRaises(ValueError):
                wm.read_data(path)


class AnalysisTests(unittest.TestCase):


    def test_monthly_statistics(self):
        rows = wm.monthly_statistics(make_records([10, 20, 30]))
        pm25 = [r for r in rows if r["variable"] == "pm25"][0]
        self.assertEqual(pm25["min"], 10)
        self.assertEqual(pm25["max"], 30)
        self.assertEqual(pm25["mean"], 20)
        self.assertEqual(pm25["max_day"], 3)

    def test_all_months_and_variables(self):
        rows = wm.monthly_statistics(wm.read_data())
        self.assertEqual(len(rows), 24 * 6)

    def test_comparison_with_standards(self):
        rows = wm.compare_with_standards(make_records([40.0, 60.0, 20.0]))
        pm25 = [r for r in rows if r["variable"] == "pm25"][0]
        self.assertEqual(pm25["who_annual_result"], "Non-compliant")      # 40 > 5
        self.assertEqual(pm25["qcvn_annual_result"], "Non-compliant")     # 40 > 25
        self.assertEqual(pm25["days_above_who_24h"], 3)
        self.assertEqual(pm25["days_above_qcvn_24h"], 1)


class CleaningTests(unittest.TestCase):


    def test_impossible_values_are_replaced(self):
        records = make_records([20.0, -5.0, 9999.0])
        records[0]["humidity"] = 135.0
        report = wm.clean_records(records)
        self.assertIsNone(records[1]["pm25"])
        self.assertIsNone(records[2]["pm25"])
        self.assertIsNone(records[0]["humidity"])
        self.assertEqual(report["pm25"]["invalid"], 2)
        self.assertEqual(report["humidity"]["invalid"], 1)

    def test_valid_values_are_not_changed(self):
        records = make_records([20.0, 30.0])
        report = wm.clean_records(records)
        self.assertEqual(records[0]["pm25"], 20.0)
        self.assertEqual(report["pm25"], {"missing": 0, "invalid": 0})

    def test_missing_values_are_counted(self):
        report = wm.clean_records(make_records([20.0, None, NAN]))
        self.assertEqual(report["pm25"]["missing"], 2)

    def test_boundary_values_are_valid(self):
        records = make_records([0.0, 500.0])
        self.assertEqual(wm.clean_records(records)["pm25"]["invalid"], 0)


class CompletenessTests(unittest.TestCase):


    def test_few_valid_days_give_insufficient_data(self):
        self.assertEqual(wm.classify_annual(40, 2, 10, 25), "Insufficient data")

    def test_enough_valid_days_give_a_result(self):
        self.assertEqual(wm.classify_annual(40, 8, 10, 25), "Non-compliant")
        self.assertEqual(wm.classify_annual(20, 8, 10, 25), "Compliant")

    def test_comparison_uses_the_rule(self):
        records = make_records([40.0, NAN, NAN, NAN])
        row = [r for r in wm.compare_with_standards(records) if r["variable"] == "pm25"][0]
        self.assertEqual(row["valid_days"], 1)
        self.assertEqual(row["qcvn_annual_result"], "Insufficient data")


class ProgramTests(unittest.TestCase):


    def test_full_run_creates_files(self):
        with tempfile.TemporaryDirectory() as folder:
            results = wm.analyse(output_folder=folder)
            self.assertTrue(os.path.exists(os.path.join(folder, "alerts.csv")))
            self.assertTrue(os.path.exists(os.path.join(folder, "pm25_daily.png")))
            self.assertGreater(len(results["alerts"]), 0)

    def test_faulty_file_does_not_crash_the_program(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "faulty.csv")
            rows = gd.generate_rows()[:40]
            rows[3]["humidity"] = 135
            rows[5]["pm25"] = -5
            rows[7]["temperature"] = "abc"
            gd.write_csv(rows, path)
            results = wm.analyse(path, os.path.join(folder, "out"))
            self.assertEqual(results["quality"]["humidity"]["invalid"], 1)
            self.assertEqual(results["quality"]["pm25"]["invalid"], 1)
            self.assertGreaterEqual(results["quality"]["temperature"]["missing"], 1)

    def test_missing_file_returns_error_code(self):
        self.assertEqual(wm.main(["--data", "no_such_file.csv"]), 1)

    def test_dashboard_key_events(self):
        with tempfile.TemporaryDirectory() as folder:
            board = wm.Dashboard(wm.read_data(), folder)
            board.on_key(SimpleNamespace(key="right"))
            self.assertEqual(board.months[board.month_index], (2024, 2))
            board.on_key(SimpleNamespace(key="left"))
            board.on_key(SimpleNamespace(key="left"))          # cannot go before Jan 2024
            self.assertEqual(board.month_index, 0)
            board.on_key(SimpleNamespace(key="up"))
            self.assertEqual(wm.VARIABLES[board.variable_index], "pm10")
            board.on_key(SimpleNamespace(key="e"))
            self.assertTrue(os.path.exists(board.last_export))


if __name__ == "__main__":
    unittest.main()
