import argparse, csv, random, threading, time
from concurrent.futures import ThreadPoolExecutor
import requests

URL = "http://emi.local/api/emi"

def one_request(session, rows, lock):
    payload = {
        "P": random.randint(10000, 5000000),
        "rate": round(random.uniform(5, 20), 2),
        "n": random.randint(6, 120),
    }
    t0 = time.time()
    status = 0
    try:
        r = session.post(URL, json=payload, timeout=10)
        status = r.status_code
        ok = (status == 200)
    except Exception:
        ok = False
    t1 = time.time()
    with lock:
        rows.append((t0, status, 1 if ok else 0, (t1 - t0) * 1000.0))

def run(rate, duration, out_csv, label):
    rows, lock = [], threading.Lock()
    workers = max(32, int(rate * 1.5))
    local = threading.local()

    def task():
        if not hasattr(local, "s"):
            local.s = requests.Session()
        one_request(local.s, rows, lock)

    start = time.time()
    total = int(rate * duration)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for i in range(total):
            delay = (start + i / rate) - time.time()
            if delay > 0:
                time.sleep(delay)
            ex.submit(task)
    end = time.time()

    rows.sort()
    with open(out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "status", "ok", "latency_ms"])
        for r in rows:
            w.writerow([f"{r[0]:.3f}", r[1], r[2], f"{r[3]:.2f}"])

    n = len(rows)
    okc = sum(r[2] for r in rows)
    lat_ok = [r[3] for r in rows if r[2]]
    avg = sum(lat_ok) / len(lat_ok) if lat_ok else float("nan")
    elapsed = end - start
    print(f"[{label}] rate={rate} dur={duration}s sent={n} ok={okc} errors={n - okc} "
          f"avg_ms={avg:.2f} actual_rate={n / elapsed:.1f}/s")
    return n, okc, avg

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rate", type=float, required=True)
    ap.add_argument("--duration", type=int, default=60)
    ap.add_argument("--out", required=True)
    ap.add_argument("--label", default="run")
    a = ap.parse_args()
    run(a.rate, a.duration, a.out, a.label)