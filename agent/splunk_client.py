import splunklib.client as client
import splunklib.results as results
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

class SplunkClient:
    def __init__(self):
        self.service = client.connect(
            host=os.getenv("SPLUNK_HOST", "localhost"),
            port=int(os.getenv("SPLUNK_PORT", 8089)),
            username=os.getenv("SPLUNK_USERNAME", "MohitMayank"),
            password=os.getenv("SPLUNK_PASSWORD"),
        )
        print("✅ Connected to Splunk successfully")

    def query(self, spl, earliest="-1h", latest="now"):
        kwargs = {
            "exec_mode": "blocking",
            "earliest_time": earliest,
            "latest_time": latest,
        }
        job = self.service.jobs.create(spl, **kwargs)
        rows = []
        for result in results.JSONResultsReader(job.results(output_mode="json", count=0)):
            if isinstance(result, dict):
                rows.append(result)
        return pd.DataFrame(rows)

    def get_metrics(self, earliest="-48h", latest="now"):
        spl = """
        search index=ops_metrics
        | table _time host cpu_pct memory_pct request_rate error_rate
        | sort _time
        """
        df = self.query(spl, earliest=earliest, latest=latest)
        if df.empty:
            print("⚠️ No data returned from Splunk")
            return df
        for col in ["cpu_pct", "memory_pct", "request_rate", "error_rate"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df["_time"] = pd.to_datetime(df["_time"], errors="coerce")
        df = df.dropna().reset_index(drop=True)
        print(f"✅ Fetched {len(df)} rows from Splunk")
        return df


if __name__ == "__main__":
    sc = SplunkClient()
    df = sc.get_metrics()
    print(df.head(10))
