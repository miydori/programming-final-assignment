
import math


def buggy_minimum(values):
    low = 0
    for value in values:
        if value < low:                
            low = value
    return low


def buggy_mean(values):

    total = 0.0
    for value in values:
        total = total + value          
    return total / len(values)


def buggy_alerts(values, limit):
    alerts = []
    for value in values:
        if value >= limit:             
            alerts.append(value)
    return alerts


def fixed_minimum(values):
    low = math.inf
    for value in values:
        if value < low:
            low = value
    return low


def fixed_mean(values):
    total = 0.0
    count = 0
    for value in values:
        if math.isnan(value):
            continue
        total = total + value
        count = count + 1
    return total / count


def fixed_alerts(values, limit):
    alerts = []
    for value in values:
        if value > limit:
            alerts.append(value)
    return alerts


def main():
    print("BUG 1 minimum of [20, 35, 50] :", buggy_minimum([20, 35, 50]), "(should be 20)")
    print("FIX 1 minimum of [20, 35, 50] :", fixed_minimum([20, 35, 50]))
    data = [10.0, math.nan, 40.0]
    print("BUG 2 mean of [10, empty, 40] :", buggy_mean(data), "(should be 25)")
    print("FIX 2 mean of [10, empty, 40] :", fixed_mean(data))
    print("BUG 3 alerts for [49.9, 50, 50.1], limit 50 :", buggy_alerts([49.9, 50, 50.1], 50))
    print("FIX 3 alerts for [49.9, 50, 50.1], limit 50 :", fixed_alerts([49.9, 50, 50.1], 50))


if __name__ == "__main__":
    main()
