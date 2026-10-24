import argparse
import csv
import math
import os
import sys

import matplotlib
import matplotlib.pyplot as plt

DATA_FILE = os.path.join("data", "hcmc_daily_2024_2025.csv")
OUTPUT_FOLDER = "output"

VARIABLES = ["temperature", "humidity", "rainfall", "pm25", "pm10", "no2"]
POLLUTANTS = ["pm25", "pm10", "no2"]
LABELS = {
    "temperature": "Temperature (C)",
    "humidity": "Humidity (%)",
    "rainfall": "Rainfall (mm)",
    "pm25": "PM2.5 (ug/m3)",
    "pm10": "PM10 (ug/m3)",
    "no2": "NO2 (ug/m3)",
}
MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


LIMITS = {
    "WHO": {"pm25": {"24h": 15, "annual": 5},
            "pm10": {"24h": 45, "annual": 15},
            "no2": {"24h": 25, "annual": 10}},
    "QCVN": {"pm25": {"24h": 50, "annual": 25},
             "pm10": {"24h": 100, "annual": 50},
             "no2": {"24h": 100, "annual": 40}},
}

ALERT_LIMITS = {"pm25": 50, "pm10": 100, "no2": 100}


VALID_RANGES = {"temperature": (15, 45), "humidity": (0, 100), "rainfall": (0, 500),
                "pm25": (0, 500), "pm10": (0, 800), "no2": (0, 300)}

MIN_VALID_SHARE = 0.75



def is_missing(value):

    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return False


def to_number(text):

    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def read_data(path=DATA_FILE):

    if not os.path.exists(path):
        raise FileNotFoundError("Data file not found: " + path
                                + " (run generate_data.py first)")
    with open(path, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for name in ["date"] + VARIABLES:
            if name not in reader.fieldnames:
                raise ValueError("Missing column in the data file: " + name)
        records = []
        for row in reader:
            year, month, day = row["date"].split("-")
            record = {"date": row["date"], "year": int(year),
                      "month": int(month), "day": int(day)}
            for variable in VARIABLES:
                record[variable] = to_number(row[variable])
            records.append(record)
    if len(records) == 0:
        raise ValueError("The data file has no rows")
    return records


def list_months(records):

    months = set()
    for record in records:
        months.add((record["year"], record["month"]))
    return sorted(months)


def records_of_month(records, year, month):

    selected = []
    for record in records:
        if record["year"] == year and record["month"] == month:
            selected.append(record)
    return selected


def compute_stats(values, labels=None):

    count = 0
    total = 0.0
    low = math.inf
    high = -math.inf
    low_label = None
    high_label = None
    for index in range(len(values)):
        value = values[index]
        label = None
        if labels is not None:
            label = labels[index]
        if is_missing(value):
            continue
        count = count + 1
        total = total + value
        if value < low:
            low = value
            low_label = label
        if value > high:
            high = value
            high_label = label
    if count == 0:
        return {"count": 0, "min": math.nan, "max": math.nan, "mean": math.nan,
                "total": math.nan, "min_label": None, "max_label": None}
    return {"count": count, "min": low, "max": high, "mean": total / count,
            "total": total, "min_label": low_label, "max_label": high_label}


class Alert:


    def __init__(self, date, variable, value, limit):
        self.date = date
        self.variable = variable
        self.value = value
        self.limit = limit

    def severity(self):

        ratio = self.value / self.limit
        if ratio >= 2.0:
            return "CRITICAL"
        if ratio >= 1.5:
            return "HIGH"
        return "WARNING"

    def to_row(self):

        return {"date": self.date, "variable": self.variable,
                "value": round(self.value, 1), "limit": self.limit,
                "severity": self.severity()}


def find_alerts(records, limits=ALERT_LIMITS):

    alerts = []
    for variable in limits:
        for record in records:
            value = record[variable]
            if is_missing(value):
                continue
            if value > limits[variable]:
                alerts.append(Alert(record["date"], variable, value, limits[variable]))
    alerts.sort(key=alert_sort_key)
    return alerts


def alert_sort_key(alert):

    return (alert.date, alert.variable)


def classify(value, limit):

    if is_missing(value):
        return "No data"
    if value <= limit:
        return "Compliant"
    return "Non-compliant"


def count_days_above(records, variable, limit):

    days = 0
    for record in records:
        value = record[variable]
        if not is_missing(value) and value > limit:
            days = days + 1
    return days


def clean_records(records):

    report = {}
    for variable in VARIABLES:
        low, high = VALID_RANGES[variable]
        missing = 0
        invalid = 0
        for record in records:
            value = record[variable]
            if is_missing(value):
                missing = missing + 1
            elif value < low or value > high:
                record[variable] = None
                invalid = invalid + 1
        report[variable] = {"missing": missing, "invalid": invalid}
    return report


def classify_annual(mean, valid_days, total_days, limit):

    if valid_days < MIN_VALID_SHARE * total_days:
        return "Insufficient data"
    return classify(mean, limit)


def monthly_statistics(records):

    rows = []
    for year, month in list_months(records):
        month_records = records_of_month(records, year, month)
        days = [record["day"] for record in month_records]
        for variable in VARIABLES:
            values = [record[variable] for record in month_records]
            stats = compute_stats(values, days)
            rows.append({"year": year, "month": month, "variable": variable,
                         "valid_days": stats["count"],
                         "min": stats["min"], "min_day": stats["min_label"],
                         "mean": stats["mean"],
                         "max": stats["max"], "max_day": stats["max_label"],
                         "total": stats["total"]})
    return rows


def compare_with_standards(records):

    rows = []
    years = sorted(set(record["year"] for record in records))
    for year in years:
        year_records = [r for r in records if r["year"] == year]
        for variable in POLLUTANTS:
            stats = compute_stats([r[variable] for r in year_records])
            mean = stats["mean"]
            valid_days = stats["count"]
            total_days = len(year_records)
            who = LIMITS["WHO"][variable]
            qcvn = LIMITS["QCVN"][variable]
            rows.append({
                "year": year, "variable": variable, "yearly_mean": round(mean, 1),
                "valid_days": valid_days,
                "who_annual_limit": who["annual"],
                "who_annual_result": classify_annual(mean, valid_days, total_days, who["annual"]),
                "qcvn_annual_limit": qcvn["annual"],
                "qcvn_annual_result": classify_annual(mean, valid_days, total_days,
                                                      qcvn["annual"]),
                "days_above_who_24h": count_days_above(year_records, variable, who["24h"]),
                "days_above_qcvn_24h": count_days_above(year_records, variable, qcvn["24h"])})
    return rows


def save_csv(rows, filename, output_folder=OUTPUT_FOLDER):

    os.makedirs(output_folder, exist_ok=True)
    path = os.path.join(output_folder, filename)
    if len(rows) == 0:
        rows = [{"note": "no rows"}]
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return path


def print_month_table(stats_rows, variable, year):

    print(f"\nMonthly statistics of {LABELS[variable]} in {year}")
    print("Month   Min (day)      Mean   Max (day)")
    for row in stats_rows:
        if row["variable"] == variable and row["year"] == year:
            print(f"{MONTH_NAMES[row['month'] - 1]:>5} {row['min']:>7.1f} ({row['min_day']:>2})"
                  f" {row['mean']:>7.1f} {row['max']:>7.1f} ({row['max_day']:>2})")


def print_quality_report(report, total_days):

    print(f"\nData quality ({total_days} days)")
    for variable in VARIABLES:
        row = report[variable]
        print(f"  {variable:<12} missing {row['missing']:>3}   invalid {row['invalid']:>3}")


def print_alerts(alerts):

    print("\nAlerts (daily value above the QCVN 24-hour limit): " + str(len(alerts)))
    for alert in alerts[:5]:
        row = alert.to_row()
        print(f"  {row['date']} {row['variable']} = {row['value']}"
              f" (limit {row['limit']}) {row['severity']}")
    if len(alerts) > 5:
        print("  ... see alerts.csv for all alerts")


def print_comparison(comparison):

    print("\nComparison with the standards (yearly mean and days above the 24-hour limits)")
    for row in comparison:
        print(f"  {row['year']} {row['variable']:<5} mean {row['yearly_mean']:>5.1f}"
              f" | WHO {row['who_annual_result']:<14} QCVN {row['qcvn_annual_result']}")
        print(f"        days above the 24h limit: WHO {row['days_above_who_24h']:>3},"
              f" QCVN {row['days_above_qcvn_24h']:>3}")


def save_chart(figure, filename, output_folder=OUTPUT_FOLDER):

    os.makedirs(output_folder, exist_ok=True)
    path = os.path.join(output_folder, filename)
    figure.tight_layout()
    figure.savefig(path, dpi=130)
    plt.close(figure)
    return path


def chart_pm25_daily(records, output_folder=OUTPUT_FOLDER):

    x_values = list(range(len(records)))
    y_values = []
    for record in records:
        value = record["pm25"]
        y_values.append(math.nan if is_missing(value) else value)
    figure, axes = plt.subplots(figsize=(10, 4))
    axes.plot(x_values, y_values, color="#1f77b4", linewidth=0.8, label="Daily PM2.5")
    axes.axhline(LIMITS["WHO"]["pm25"]["24h"], color="green", linestyle="--",
                 label="WHO 24h limit (15)")
    axes.axhline(LIMITS["QCVN"]["pm25"]["24h"], color="red", linestyle="--",
                 label="QCVN 24h limit (50)")
    for x_value, y_value in zip(x_values, y_values):
        if not is_missing(y_value) and y_value > ALERT_LIMITS["pm25"]:
            axes.plot(x_value, y_value, "ro")
    tick_positions = []
    tick_names = []
    for index, record in enumerate(records):
        if record["day"] == 1 and record["month"] in (1, 4, 7, 10):
            tick_positions.append(index)
            tick_names.append(f"{MONTH_NAMES[record['month'] - 1]} {record['year']}")
    axes.set_xticks(tick_positions)
    axes.set_xticklabels(tick_names)
    axes.set_title("Ho Chi Minh City - daily PM2.5")
    axes.set_ylabel(LABELS["pm25"])
    axes.grid(alpha=0.3)
    axes.legend(loc="upper right")
    return save_chart(figure, "pm25_daily.png", output_folder)


def chart_monthly_means(stats_rows, output_folder=OUTPUT_FOLDER):

    figure, all_axes = plt.subplots(2, 3, figsize=(13, 7))
    for axes, variable in zip(all_axes.flatten(), VARIABLES):
        months = []
        means = []
        for row in stats_rows:
            if row["variable"] == variable:
                months.append(len(months) + 1)
                if variable == "rainfall":
                    means.append(row["total"])
                else:
                    means.append(row["mean"])
        if variable == "rainfall":
            axes.bar(months, means, color="#17becf")
            axes.set_title("Rainfall - monthly total (mm)")
        else:
            axes.plot(months, means, marker="o", markersize=3)
            axes.set_title(LABELS[variable] + " - monthly mean")
        axes.set_xlabel("Month number (1 = Jan 2024, 24 = Dec 2025)")
        axes.grid(alpha=0.3)
    figure.suptitle("Ho Chi Minh City - monthly values of the six variables")
    return save_chart(figure, "monthly_dashboard.png", output_folder)


def chart_pm25_months(stats_rows, output_folder=OUTPUT_FOLDER):

    months = []
    lows = []
    means = []
    highs = []
    names = []
    for row in stats_rows:
        if row["variable"] == "pm25":
            months.append(len(months) + 1)
            lows.append(row["min"])
            means.append(row["mean"])
            highs.append(row["max"])
            names.append(f"{MONTH_NAMES[row['month'] - 1]}\n{row['year']}")
    figure, axes = plt.subplots(figsize=(10, 4))
    axes.fill_between(months, lows, highs, alpha=0.25, label="Min - Max")
    axes.plot(months, means, marker="o", label="Mean")
    axes.axhline(LIMITS["QCVN"]["pm25"]["24h"], color="red", linestyle="--",
                 label="QCVN 24h limit")
    axes.set_xticks(months[::3])
    axes.set_xticklabels(names[::3])
    axes.set_title("Ho Chi Minh City - monthly minimum, mean and maximum of PM2.5")
    axes.set_ylabel(LABELS["pm25"])
    axes.grid(alpha=0.3)
    axes.legend()
    return save_chart(figure, "pm25_months.png", output_folder)


def chart_annual(comparison, output_folder=OUTPUT_FOLDER):

    figure, all_axes = plt.subplots(1, 3, figsize=(12, 4))
    for axes, variable in zip(all_axes, POLLUTANTS):
        years = []
        means = []
        for row in comparison:
            if row["variable"] == variable:
                years.append(str(row["year"]))
                means.append(row["yearly_mean"])
        axes.bar(years, means, color="#1f77b4")
        axes.axhline(LIMITS["WHO"][variable]["annual"], color="green", linestyle="--",
                     label="WHO annual")
        axes.axhline(LIMITS["QCVN"][variable]["annual"], color="red", linestyle="--",
                     label="QCVN annual")
        axes.set_title(LABELS[variable] + " - yearly mean")
        axes.legend()
    return save_chart(figure, "annual_comparison.png", output_folder)


class Dashboard:

    def __init__(self, records, output_folder=OUTPUT_FOLDER):
        self.records = records
        self.output_folder = output_folder
        self.months = list_months(records)
        self.month_index = 0
        self.variable_index = VARIABLES.index("pm25")
        self.last_export = None
        self.figure, self.axes = plt.subplots(figsize=(9, 5))
        self.figure.canvas.mpl_connect("key_press_event", self.on_key)
        self.draw()

    def draw(self):

        year, month = self.months[self.month_index]
        variable = VARIABLES[self.variable_index]
        month_records = records_of_month(self.records, year, month)
        days = [record["day"] for record in month_records]
        values = []
        for record in month_records:
            value = record[variable]
            values.append(math.nan if is_missing(value) else value)
        stats = compute_stats(values, days)
        self.axes.clear()
        self.axes.bar(days, values, color="#1f77b4")
        if variable in ALERT_LIMITS:
            self.axes.axhline(LIMITS["WHO"][variable]["24h"], color="green", linestyle="--")
            self.axes.axhline(LIMITS["QCVN"][variable]["24h"], color="red", linestyle="--")
        self.axes.set_xlabel("Day of the month")
        self.axes.set_title(f"{MONTH_NAMES[month - 1]} {year} - {LABELS[variable]}\n"
                            f"min {stats['min']:.1f} | mean {stats['mean']:.1f}"
                            f" | max {stats['max']:.1f}")
        self.figure.canvas.draw_idle()

    def on_key(self, event):

        if event.key == "right" and self.month_index < len(self.months) - 1:
            self.month_index = self.month_index + 1
        elif event.key == "left" and self.month_index > 0:
            self.month_index = self.month_index - 1
        elif event.key == "up":
            self.variable_index = (self.variable_index + 1) % len(VARIABLES)
        elif event.key == "down":
            self.variable_index = (self.variable_index - 1) % len(VARIABLES)
        elif event.key == "e":
            self.export()
            return
        self.draw()

    def export(self):
        """Save the current view."""
        os.makedirs(self.output_folder, exist_ok=True)
        year, month = self.months[self.month_index]
        name = f"view_{year}_{month:02d}_{VARIABLES[self.variable_index]}.png"
        self.last_export = os.path.join(self.output_folder, name)
        self.figure.savefig(self.last_export, dpi=130)


def analyse(path=DATA_FILE, output_folder=OUTPUT_FOLDER):

    records = read_data(path)
    quality = clean_records(records)
    stats_rows = monthly_statistics(records)
    alerts = find_alerts(records)
    comparison = compare_with_standards(records)

    quality_rows = [{"variable": v, "missing": quality[v]["missing"],
                     "invalid": quality[v]["invalid"]} for v in VARIABLES]
    save_csv(quality_rows, "data_quality.csv", output_folder)
    save_csv(stats_rows, "monthly_statistics.csv", output_folder)
    save_csv([alert.to_row() for alert in alerts], "alerts.csv", output_folder)
    save_csv(comparison, "standards_comparison.csv", output_folder)
    chart_pm25_daily(records, output_folder)
    chart_pm25_months(stats_rows, output_folder)
    chart_monthly_means(stats_rows, output_folder)
    chart_annual(comparison, output_folder)

    print(f"Read {len(records)} days from {path}")
    print_quality_report(quality, len(records))
    last_year = records[-1]["year"]
    print_month_table(stats_rows, "pm25", last_year)
    print_alerts(alerts)
    print_comparison(comparison)
    print("\nFiles saved in the folder: " + output_folder)
    return {"records": records, "stats": stats_rows, "alerts": alerts,
            "comparison": comparison, "quality": quality}


def build_parser():
    parser = argparse.ArgumentParser(description="Weather MIS (simple version)")
    parser.add_argument("--data", default=DATA_FILE, help="CSV file with the daily data")
    parser.add_argument("--interactive", action="store_true",
                        help="open the interactive chart")
    return parser


def main(argv=None):

    args = build_parser().parse_args(argv)
    if not args.interactive:
        matplotlib.use("Agg")
    try:
        results = analyse(args.data)
    except (OSError, ValueError, KeyError) as error:
        print("ERROR: " + str(error))
        return 1
    if args.interactive:
        Dashboard(results["records"])
        plt.show()
    return 0


if __name__ == "__main__":
    sys.exit(main())
