import argparse, csv, os, random, subprocess, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
URL = "http://emi.local/api/emi"
PHASES = [(120, 10), (300, 100), (180, 10)]  # (seconds, req/s)
TOTAL = sum(p[0] for p in PHASES)
MAX_LATE = 2.0   # seconds; requests later than this are dropped by the generator
TIMEOUT = 5

def rate_at(el):
    acc = 0
    for dur, r in PHASES:
        acc += dur
        if el < acc:
            return r
    return PHASES[-1][1]

def hpa_loop(prefix, stop):
    with open(prefix + "_hpa.csv", "w", newline="") as f, \
         open(prefix + "_hpa_raw.txt", "w") as raw:
        w = csv.writer(f)
        w.writerow(["timestamp", "hpa_line"])
        nxt = time.time()
        while not stop.is_set():
            ts = time.time()
            try:
                out = subprocess.run(
                    ["kubectl", "get", "hpa", "emi-web", "-n", "emi", "--no-headers"],
                    capture_output=True, text=True, timeout=20).stdout.strip()
            except Exception as e:
                out = "ERROR " + str(e)
            w.writerow([f"{ts:.3f}", out])
            raw.write(f"{ts:.3f}  {out}\n")
            f.flush(); raw.flush()
            nxt += 15
            while time.time() < nxt and not stop.is_set():
                time.sleep(0.2)

def main(prefix, cooldown):
    rows, lock = [], threading.Lock()
    local = threading.local()

    def task(t_sched):
        now = time.time()
        if now - t_sched > MAX_LATE:
            with lock:
                rows.append((t_sched, -1, 0, 0.0, (now - t_sched) * 1000.0))
            return
        if not hasattr(local, "s"):
            local.s = requests.Session()
        payload = {"P": random.randint(10000, 5000000),
                   "rate": round(random.uniform(5, 20), 2),
                   "n": random.randint(6, 120)}
        t0 = time.time()
        status, ok = 0, 0
        try:
            r = local.s.post(URL, json=payload, timeout=TIMEOUT)
            status = r.status_code
            ok = 1 if status == 200 else 0
        except Exception:
            pass
        t1 = time.time()
        with lock:
            rows.append((t_sched, status, ok, (t1 - t0) * 1000.0, (t0 - t_sched) * 1000.0))

    start = time.time()
    with open(prefix + "_meta.txt", "w") as m:
        m.write(f"start_epoch={start:.3f}\nphases={PHASES}\ncooldown={cooldown}\n")
    prof = subprocess.Popen([sys.executable, os.path.join(HERE, "profiler.py"),
                             "--prefix", prefix, "--duration", str(TOTAL + cooldown + 20)])
    stop = threading.Event()
    th = threading.Thread(target=hpa_loop, args=(prefix, stop))
    th.start()
    print("autoscaling test started", time.strftime("%H:%M:%S"), flush=True)

    nxt = start
    ex = ThreadPoolExecutor(max_workers=200)
    while nxt - start < TOTAL:
        delay = nxt - time.time()
        if delay > 0:
            time.sleep(delay)
        ex.submit(task, nxt)
        nxt += 1.0 / rate_at(nxt - start)
    print("load schedule finished", time.strftime("%H:%M:%S"), flush=True)
    ex.shutdown(wait=True)
    print("in-flight requests done", time.strftime("%H:%M:%S"), "- cool-down logging...", flush=True)

    rows.sort()
    with open(prefix + "_load.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "status", "ok", "latency_ms", "queue_ms"])
        for r in rows:
            w.writerow([f"{r[0]:.3f}", r[1], r[2], f"{r[3]:.2f}", f"{r[4]:.2f}"])

    acc = 0
    for i, (dur, rate) in enumerate(PHASES, 1):
        sel = [r for r in rows if acc <= r[0] - start < acc + dur]
        okl = [r[3] for r in sel if r[2]]
        dropped = sum(1 for r in sel if r[1] == -1)
        avg = sum(okl) / len(okl) if okl else float("nan")
        print(f"phase{i} {rate}/s {dur}s: sent={len(sel)} ok={len(okl)} "
              f"errors={len(sel) - len(okl)} (dropped_by_generator={dropped}) avg_ms={avg:.2f}")
        acc += dur

    time.sleep(cooldown)
    stop.set()
    th.join()
    prof.wait()
    print("ALL DONE")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", default="results\\m4_hpa")
    ap.add_argument("--cooldown", type=int, default=300)
    a = ap.parse_args()
    main(a.prefix, a.cooldown)