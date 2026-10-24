

import os
import random
import tempfile
import timeit

import generate_data as gd
import weather_mis as wm

REPEAT = 3


def best_time_ms(function, number):
    return min(timeit.repeat(function, number=number, repeat=REPEAT)) / number * 1000


def built_in_stats(values):
    return min(values), max(values), sum(values) / len(values)


def experiment_1():
    print("Experiment 1: compute_stats (hand-written loop) against built-in functions")
    print(f"{'values':>8} {'loop (ms)':>11} {'built-in (ms)':>14} {'ratio':>7}  same result")
    rng = random.Random(0)
    for size in (1000, 10000, 100000):
        values = [rng.uniform(5, 60) for _ in range(size)]
        loop_ms = best_time_ms(lambda: wm.compute_stats(values), 5)
        builtin_ms = best_time_ms(lambda: built_in_stats(values), 20)
        stats = wm.compute_stats(values)
        low, high, mean = built_in_stats(values)
        same = (stats["min"] == low and stats["max"] == high
                and abs(stats["mean"] - mean) < 1e-9)
        ratio = loop_ms / builtin_ms
        print(f"{size:>8} {loop_ms:>11.3f} {builtin_ms:>14.3f} {ratio:>7.1f}  {same}")


def experiment_2():
    print("\nExperiment 2: time of monthly_statistics when the data grow")
    print(f"{'years':>6} {'days':>7} {'months':>7} {'time (ms)':>10}")
    original = (gd.START_DATE, gd.END_DATE)
    for years in (2, 10, 20):
        gd.START_DATE = original[0]
        last_year = original[0].year + years - 1
        gd.END_DATE = original[0].replace(year=last_year, month=12, day=31)
        with tempfile.TemporaryDirectory() as folder:
            path = gd.write_csv(gd.generate_rows(), os.path.join(folder, "long.csv"))
            records = wm.read_data(path)
        wm.clean_records(records)
        milliseconds = best_time_ms(lambda: wm.monthly_statistics(records), 1)
        months = len(wm.list_months(records))
        print(f"{years:>6} {len(records):>7} {months:>7} {milliseconds:>10.1f}")
    gd.START_DATE, gd.END_DATE = original


if __name__ == "__main__":
    experiment_1()
    experiment_2()
