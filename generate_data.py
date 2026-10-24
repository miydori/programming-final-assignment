
import csv
import datetime
import os
import random

SEED = 42
START_DATE = datetime.date(2024, 1, 1)
END_DATE = datetime.date(2025, 12, 31)
MISSING_RATE = 0.01
OUTPUT_FILE = os.path.join("data", "hcmc_daily_2024_2025.csv")
COLUMNS = ["date", "temperature", "humidity", "rainfall", "pm25", "pm10", "no2"]

TEMPERATURE = [26.4, 27.3, 28.6, 29.7, 29.1, 28.2, 27.8, 27.8, 27.6, 27.2, 26.9, 26.3]
HUMIDITY = [71, 70, 69, 70, 75, 79, 80, 80, 82, 82, 78, 74]
RAIN_PROBABILITY = [0.03, 0.02, 0.06, 0.17, 0.55, 0.67, 0.68, 0.65, 0.70, 0.61, 0.33, 0.13]
RAIN_ON_RAINY_DAY = [15.5, 6.7, 6.7, 8.6, 13.2, 15.6, 14.0, 13.5, 15.6, 14.5, 11.7, 12.3]
PM25_BASE = [42, 40, 34, 28, 20, 15, 13, 14, 16, 19, 27, 38]
NO2_BASE = [38, 37, 35, 32, 28, 25, 24, 24, 26, 28, 32, 37]


def make_day(day, rng, previous_pm25):
    i = day.month - 1                         

    rain = 0.0
    if rng.random() < RAIN_PROBABILITY[i]:    
        rain = min(rng.expovariate(1 / RAIN_ON_RAINY_DAY[i]), 150)
    heavy_rain = rain >= 5

    temperature = TEMPERATURE[i] + rng.gauss(0, 1.0)
    if heavy_rain:
        temperature = temperature - 1.2       

    humidity = HUMIDITY[i] + rng.gauss(0, 4)
    if rain > 0:
        humidity = humidity + 6           
    humidity = max(40, min(100, humidity))

    pm25 = 0.6 * previous_pm25 + 0.4 * PM25_BASE[i] * rng.uniform(0.5, 1.6)
    if heavy_rain:
        pm25 = pm25 * 0.7                     
    pm25 = max(5, pm25)

    pm10 = pm25 * rng.uniform(1.4, 1.8)       

    no2 = NO2_BASE[i] * rng.uniform(0.8, 1.2)
    if day.weekday() >= 5:
        no2 = no2 * 0.85                      
    if heavy_rain:
        no2 = no2 * 0.9

    values = {"temperature": round(temperature, 1), "humidity": round(humidity),
              "rainfall": round(rain, 1), "pm25": round(pm25, 1),
              "pm10": round(pm10, 1), "no2": round(no2, 1)}
    return values, pm25


def generate_rows(seed=SEED):
    rng = random.Random(seed)               
    rows = []
    previous_pm25 = PM25_BASE[0]
    day = START_DATE
    while day <= END_DATE:
        values, previous_pm25 = make_day(day, rng, previous_pm25)
        row = {"date": day.isoformat()}
        for name in COLUMNS[1:]:
            if rng.random() < MISSING_RATE:
                row[name] = ""                
            else:
                row[name] = values[name]
        rows.append(row)
        day = day + datetime.timedelta(days=1)
    return rows


def write_csv(rows, path=OUTPUT_FILE):
    """Save the rows as a CSV file."""
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return path


if __name__ == "__main__":
    data = generate_rows()
    print("Saved", len(data), "days in", write_csv(data))
