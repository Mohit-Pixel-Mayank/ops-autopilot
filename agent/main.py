import time
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(__file__))

from splunk_client import SplunkClient
from anomaly import detect_anomalies, summarise_anomalies
from runbook import generate_runbook

POLL_INTERVAL = 60

last_summary = None

def run_agent():
    global last_summary

    print("=" * 60)
    print("🤖 Ops Autopilot — AI Incident Detection Agent")
    print("=" * 60)
    

    sc = SplunkClient()
    cycle = 0

    while True:
        cycle += 1
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[Cycle {cycle}] Checking at {now}...")

        try:
            df = sc.get_metrics(earliest="-48h", latest="now")

            if df.empty:
                print("⚠️  No metrics data found. Waiting...")
                time.sleep(POLL_INTERVAL)
                continue

            anomaly_df = detect_anomalies(df)
            summary    = summarise_anomalies(anomaly_df)

            if not summary:
                print("✅ All systems normal. No anomalies detected.")
            elif summary == last_summary:
                print("ℹ️ Same anomalies already processed.")
                print("ℹ️ Skipping duplicate runbook generation.")
            else:
                print(f"\n🚨 {len(summary)} anomaly type(s) detected!")
                for s in summary:
                    print(f"   → {s['label']} | {s['metric']} = "
                          f"{s['peak_value']} (z={s['peak_z']})")

                print("\n📋 Generating runbook...")
                runbook = generate_runbook(summary)

                os.makedirs("runbooks", exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filepath  = f"runbooks/incident_{timestamp}.md"
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(runbook)

                print(f"✅ Runbook saved → {filepath}")
                last_summary = summary
                print("\n" + "─" * 50)
                print(runbook[:600] + "..." if len(runbook) > 600 else runbook)
                print("─" * 50)

        except Exception as e:
            print(f"❌ Agent error: {e}")

        print(f"\n⏱️  Next check in {POLL_INTERVAL}s... (Ctrl+C to stop)")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    try:
        run_agent()
    except KeyboardInterrupt:
        print("\n\n🛑 Ops Autopilot stopped by user.")