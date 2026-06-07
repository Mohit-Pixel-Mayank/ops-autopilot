import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

np.random.seed(42)

def generate_metrics(hours=48, interval_seconds=60):
    timestamps = []
    cpu = []
    memory = []
    request_rate = []
    error_rate = []

    base_time = datetime.now() - timedelta(hours=hours)

    for i in range(hours * 60):
        t = base_time + timedelta(seconds=i * interval_seconds)
        timestamps.append(t.strftime("%Y-%m-%dT%H:%M:%S"))

        hour_of_day = t.hour
        daily_pattern = 0.3 * np.sin(2 * np.pi * hour_of_day / 24)

        cpu_val = 35 + daily_pattern * 20 + np.random.normal(0, 3)
        mem_val = 55 + daily_pattern * 10 + np.random.normal(0, 2)
        req_val = 200 + daily_pattern * 100 + np.random.normal(0, 15)
        err_val = 0.5 + np.random.normal(0, 0.1)

        # Anomaly 1: CPU spike at hour 10
        if 10 * 60 <= i < 10 * 60 + 15:
            cpu_val += np.random.uniform(45, 55)
            err_val += np.random.uniform(3, 6)

        # Anomaly 2: Memory leak at hour 25
        if 25 * 60 <= i < 25 * 60 + 30:
            mem_val += (i - 25 * 60) * 0.8
            req_val -= np.random.uniform(80, 120)

        # Anomaly 3: Traffic spike at hour 38
        if 38 * 60 <= i < 38 * 60 + 20:
            req_val += np.random.uniform(400, 600)
            cpu_val += np.random.uniform(20, 30)

        cpu.append(round(min(max(cpu_val, 0), 100), 2))
        memory.append(round(min(max(mem_val, 0), 100), 2))
        request_rate.append(round(max(req_val, 0), 2))
        error_rate.append(round(max(err_val, 0), 4))

    df = pd.DataFrame({
        "_time": timestamps,
        "host": "prod-server-01",
        "cpu_pct": cpu,
        "memory_pct": memory,
        "request_rate": request_rate,
        "error_rate": error_rate
    })

    os.makedirs("data", exist_ok=True)
    output_path = "data/metrics.csv"
    df.to_csv(output_path, index=False)
    print(f"✅ Generated {len(df)} rows → {output_path}")
    print(f"✅ Anomalies injected at hours: 10 (CPU spike), 25 (memory leak), 38 (traffic spike)")
    return df

if __name__ == "__main__":
    df = generate_metrics()
    print(df.head(10))