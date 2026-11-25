"""Graphs for Milestone 4. Run from the project folder:
    python scripts\\make_graphs.py
Reads results\\ and writes graph1.png, graph2.png, graph3.png into results\\."""
import argparse, csv, os, subprocess
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def read_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))

def cpu_request_m(arg):
    if arg:
        return float(arg)
    try:
        out = subprocess.run(
            ["kubectl", "get", "deploy", "emi-web", "-n", "emi", "-o",
             "jsonpath={.spec.template.spec.containers[0].resources.requests.cpu}"],
            capture_output=True, text=True, timeout=20).stdout.strip()
        if out.endswith("m"):
            return float(out[:-1])
        if out:
            return float(out) * 1000
    except Exception:
        pass
    raise SystemExit("CPU request not found. Run again with --cpu-request-m <millicores>")

def graph1(res):
    rows = read_csv(os.path.join(res, "m4_summary.csv"))
    fig, ax = plt.subplots(figsize=(8, 5), dpi=200)
    for n, c, m in zip(("1", "2", "3"), ("#1f77b4", "#d95f02", "#2ca02c"), "osd"):
        pts = sorted((float(r["rate"]), float(r["avg_ms"])) for r in rows if r["replicas"] == n)
        ax.plot([p[0] for p in pts], [p[1] for p in pts], marker=m, color=c, lw=2,
                label=f"{n} replica" + ("s" if n != "1" else ""))
    ax.set_xlabel("Request rate (req/s)"); ax.set_ylabel("Average response time (ms)")
    ax.set_title("Graph 1: Average response time vs request rate")
    ax.set_xticks([10, 25, 50, 100, 200]); ax.grid(alpha=.3); ax.legend()
    fig.tight_layout(); fig.savefig(os.path.join(res, "graph1.png")); plt.close(fig)

def graph2(res, req_m, prefix):
    rows = [r for r in read_csv(prefix + "_pods.csv") if r["pod"].startswith("emi-web")]
    t0 = min(float(r["timestamp"]) for r in rows)
    series = {}
    for r in rows:
        series.setdefault(r["pod"], []).append(
            (float(r["timestamp"]) - t0, float(r["cpu_millicores"]) / req_m * 100))
    fig, ax = plt.subplots(figsize=(9, 5), dpi=200)
    for pod, pts in sorted(series.items()):
        pts.sort()
        ax.plot([p[0] for p in pts], [p[1] for p in pts], marker="o", lw=2, label=pod)
    ax.set_xlabel("Time (s)"); ax.set_ylabel(f"CPU utilization (% of {req_m:g}m request)")
    ax.set_title("Graph 2: CPU utilization per pod, 100 req/s, 3 replicas")
    ax.grid(alpha=.3); ax.legend(); fig.tight_layout()
    fig.savefig(os.path.join(res, "graph2.png")); plt.close(fig)

def graph3(res, req_m, prefix):
    meta = dict(l.strip().split("=", 1) for l in open(prefix + "_meta.txt") if "=" in l)
    t0 = float(meta["start_epoch"])
    # request rate: scheduled requests per 15 s bin
    load = read_csv(prefix + "_load.csv")
    bins = {}
    for r in load:
        b = int((float(r["timestamp"]) - t0) // 15)
        bins[b] = bins.get(b, 0) + 1
    rx = [b * 15 / 60 for b in sorted(bins)]
    ry = [bins[b] / 15 for b in sorted(bins)]
    # average CPU of emi-web pods per kubectl top sample
    per_ts = {}
    for r in read_csv(prefix + "_pods.csv"):
        if r["pod"].startswith("emi-web"):
            per_ts.setdefault(float(r["timestamp"]), []).append(float(r["cpu_millicores"]) / req_m * 100)
    cx = [(t - t0) / 60 for t in sorted(per_ts)]
    cy = [sum(per_ts[t]) / len(per_ts[t]) for t in sorted(per_ts)]
    # replicas from kubectl get hpa
    hx, hy = [], []
    for r in read_csv(prefix + "_hpa.csv"):
        tok = r["hpa_line"].split()
        if len(tok) >= 8 and tok[-2].isdigit():
            hx.append((float(r["timestamp"]) - t0) / 60); hy.append(int(tok[-2]))
    fig, ax = plt.subplots(3, 1, figsize=(9, 9), dpi=200, sharex=True)
    ax[0].step(rx, ry, where="post", color="#1f77b4", lw=2); ax[0].set_ylabel("Request rate (req/s)")
    ax[1].plot(cx, cy, color="#d95f02", marker="o", lw=2)
    ax[1].axhline(50, color="gray", ls="--", lw=1, label="HPA target 50%"); ax[1].legend()
    ax[1].set_ylabel("Avg CPU utilization (%)")
    ax[2].step(hx, hy, where="post", color="#2ca02c", marker="o", lw=2)
    ax[2].set_ylabel("Web replicas"); ax[2].set_ylim(0, 5.5); ax[2].set_yticks(range(0, 6))
    ax[2].set_xlabel("Time (minutes)")
    for a in ax: a.grid(alpha=.3)
    ax[0].set_title("Graph 3: Autoscaling test (shared time axis)")
    fig.tight_layout(); fig.savefig(os.path.join(res, "graph3.png")); plt.close(fig)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results")
    ap.add_argument("--cpu-request-m", default=None, help="web pod CPU request in millicores")
    ap.add_argument("--run3", default="m4_r3_rate100", help="prefix of the 3-replica 100 req/s run")
    ap.add_argument("--hpa", default="m4_hpa", help="prefix of the autoscaling test")
    a = ap.parse_args()
    graph1(a.results)
    req = cpu_request_m(a.cpu_request_m)
    graph2(a.results, req, os.path.join(a.results, a.run3))
    graph3(a.results, req, os.path.join(a.results, a.hpa))
    print("saved graph1.png, graph2.png, graph3.png in", a.results)