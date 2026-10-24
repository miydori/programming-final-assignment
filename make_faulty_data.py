
import csv

SOURCE = "data/hcmc_daily_2024_2025.csv"
TARGET = "data/faulty_example.csv"
ERRORS = [(10, "humidity", "135"),        # humidity cannot be above 100 %
          (50, "pm25", "-5"),             # a concentration cannot be negative
          (100, "temperature", "abc"),    # text instead of a number
          (200, "no2", "9999"),           # sensor error: far too large
          (300, "rainfall", "-20")]       # rainfall cannot be negative


def main():
    with open(SOURCE, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        columns = reader.fieldnames
        rows = list(reader)
    for row_number, column, wrong_value in ERRORS:
        rows[row_number][column] = wrong_value
    with open(TARGET, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    print("Saved " + TARGET + " with " + str(len(ERRORS)) + " deliberate errors")


if __name__ == "__main__":
    main()
