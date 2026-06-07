import pandas as pd
import numpy as np

THRESHOLDS = {
    "cpu_pct":      {"z_score": 2.5, "label": "CPU spike"},
    "memory_pct":   {"z_score": 2.5, "label": "Memory leak"},
    "request_rate": {"z_score": 3.0, "label": "Traffic spike"},
    "error_rate":   {"z_score": 2.5, "label": "Error rate surge"},
}

def detect_anomalies(df: pd.DataFrame, window: int = 60) -> pd.DataFrame:
    anomalies = []
    for metric, config in THRESHOLDS.items():
        if metric not in df.columns:
            continue
        series = df[metric].copy()
        rolling_mean = series.rolling(window=window, min_periods=10).mean()
        rolling_std  = series.rolling(window=window, min_periods=10).std()
        z_scores = (series - rolling_mean) / (rolling_std + 1e-9)
        flagged = df[z_scores.abs() > config["z_score"]].copy()
        if flagged.empty:
            continue
        flagged["metric"]    = metric
        flagged["z_score"]   = z_scores[flagged.index].round(3)
        flagged["value"]     = flagged[metric]
        flagged["label"]     = config["label"]
        flagged["threshold"] = config["z_score"]
        anomalies.append(flagged[["_time", "host", "metric",
                                   "value", "z_score", "label", "threshold"]])

    if not anomalies:
        return pd.DataFrame()

    result = pd.concat(anomalies).sort_values("_time").reset_index(drop=True)
    return result

def summarise_anomalies(anomaly_df: pd.DataFrame) -> list[dict]:
    if anomaly_df.empty:
        return []
    groups = []
    for metric, group in anomaly_df.groupby("metric"):
        peak_idx  = group["z_score"].abs().idxmax()
        peak_row  = group.loc[peak_idx]
        groups.append({
            "metric":     metric,
            "label":      peak_row["label"],
            "count":      len(group),
            "peak_value": round(float(peak_row["value"]), 2),
            "peak_z":     round(float(peak_row["z_score"]), 2),
            "peak_time":  str(peak_row["_time"]),
            "host":       peak_row["host"],
        })
    return groups


if __name__ == "__main__":
    from splunk_client import SplunkClient
    sc  = SplunkClient()
    df  = sc.get_metrics()
    ano = detect_anomalies(df)
    print(f"\n🔍 Total anomalous data points: {len(ano)}")
    summary = summarise_anomalies(ano)
    for s in summary:
        print(f"\n⚠️  {s['label']} on {s['host']}")
        print(f"   Metric:     {s['metric']}")
        print(f"   Peak value: {s['peak_value']}")
        print(f"   Z-score:    {s['peak_z']}")
        print(f"   Peak time:  {s['peak_time']}")
        print(f"   # of points flagged: {s['count']}")