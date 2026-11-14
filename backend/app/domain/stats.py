from math import sqrt
from statistics import mean
from typing import Iterable


def consumption_stats(rates: Iterable[float]) -> dict[str, float | int]:
    values = list(rates)
    if not values:
        return {"mean": 0.0, "standard_deviation": 0.0, "count": 0}
    average = mean(values)
    variance = sum((value - average) ** 2 for value in values) / len(values)
    return {"mean": average, "standard_deviation": sqrt(variance), "count": len(values)}


def baseline(rates: list[float], window_days: int) -> dict[str, float | int]:
    window = max(1, window_days)
    return consumption_stats(rates[-window:])


def detect_anomaly(
    rates: list[float], latest: float, z_threshold: float = 2.0, min_points: int = 4
) -> dict[str, float | bool | None]:
    historical = rates[:-1] if rates and rates[-1] == latest else rates
    if len(historical) < min_points:
        return {"z_score": None, "direction": None, "percent_change": None, "flagged": False, "insufficient_data": True}
    stats = consumption_stats(historical)
    average = float(stats["mean"])
    deviation = float(stats["standard_deviation"])
    percent_change = ((latest - average) / average * 100) if average else None
    z_score = (latest - average) / deviation if deviation else 0.0
    return {
        "z_score": z_score,
        "direction": "above" if latest >= average else "below",
        "percent_change": percent_change,
        "flagged": abs(z_score) >= z_threshold if deviation else latest != average,
        "insufficient_data": False,
    }


def compare_periods(rates_a: Iterable[float], rates_b: Iterable[float]) -> dict[str, float | None]:
    a, b = list(rates_a), list(rates_b)
    mean_a = mean(a) if a else None
    mean_b = mean(b) if b else None
    change = ((mean_b - mean_a) / mean_a * 100) if mean_a else None
    return {"mean_a": mean_a, "mean_b": mean_b, "percent_change": change}


def sustained_rise(rates: list[float], window: int = 3, pct: float = 0.2) -> bool:
    if len(rates) < window * 2:
        return False
    baseline_mean = mean(rates[: -window])
    return all(rate > baseline_mean * (1 + pct) for rate in rates[-window:])
