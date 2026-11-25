import argparse, csv, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from loadgen import run

def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--replicas", default="1,2,3")
    ap.add_argument("--rates", default="10,25,50,100,200")
    ap.add_argument("--duration", type=int, default=60)
    ap.add_argument("--gap", type=int, default=20)
    ap.add_argument("--outdir", default="results")
    a = ap.parse_args()

    os.makedirs(a.outdir, exist_ok=True)
    summary = os.path.join(a.outdir, "m4_summary.csv")
    new = not os.path.exists(summary)

    for rep in [int(x) for x in a.replicas.split(",")]:
        print(f"\n##### scaling emi-web to {rep} replicas #####")
        sh(["kubectl", "scale", "deployment/emi-web", "-n", "emi", f"--replicas={rep}"])
        sh(["kubectl", "rollout", "status", "deployment/emi-web", "-n", "emi", "--timeout=120s"])
        time.sleep(20)
        print(sh(["kubectl", "get", "deploy", "emi-web", "-n", "emi"]).stdout)

        for rate in [float(x) for x in a.rates.split(",")]:
            r = int(rate)
            prefix = os.path.join(a.outdir, f"m4_r{rep}_rate{r}")
            label = f"replicas={rep} rate={r}"
            print(f"=== {label} START ===", flush=True)
            prof = subprocess.Popen([sys.executable, os.path.join(HERE, "profiler.py"),
                                     "--prefix", prefix, "--duration", str(a.duration + 5)])
            sent, ok, avg = run(rate, a.duration, prefix + "_load.csv", label)
            prof.wait()
            with open(summary, "a", newline="") as f:
                w = csv.writer(f)
                if new:
                    w.writerow(["replicas", "rate", "sent", "ok", "errors", "avg_ms"])
                    new = False
                w.writerow([rep, r, sent, ok, sent - ok, f"{avg:.2f}"])
            print(f"=== {label} DONE ===", flush=True)
            time.sleep(a.gap)
    print("ALL DONE")