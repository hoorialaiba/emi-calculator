import argparse, csv, subprocess, threading, time
import psutil

def host_loop(path, stop):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "host_cpu_percent"])
        psutil.cpu_percent(interval=None)
        while not stop.is_set():
            cpu = psutil.cpu_percent(interval=1)
            w.writerow([f"{time.time():.3f}", cpu])
            f.flush()

def pods_loop(path, stop, interval=15):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "pod", "cpu_millicores", "memory_mi"])
        nxt = time.time()
        while not stop.is_set():
            ts = time.time()
            try:
                out = subprocess.run(
                    ["kubectl", "top", "pods", "-n", "emi", "--no-headers"],
                    capture_output=True, text=True, timeout=20).stdout
                for line in out.strip().splitlines():
                    p = line.split()
                    if len(p) >= 3:
                        w.writerow([f"{ts:.3f}", p[0],
                                    p[1].replace("m", ""), p[2].replace("Mi", "")])
                f.flush()
            except Exception as e:
                print("kubectl top failed:", e)
            nxt += interval
            while time.time() < nxt and not stop.is_set():
                time.sleep(0.2)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", required=True)
    ap.add_argument("--duration", type=int, required=True)
    a = ap.parse_args()
    stop = threading.Event()
    t1 = threading.Thread(target=host_loop, args=(a.prefix + "_host.csv", stop))
    t2 = threading.Thread(target=pods_loop, args=(a.prefix + "_pods.csv", stop))
    t1.start(); t2.start()
    time.sleep(a.duration)
    stop.set()
    t1.join(); t2.join()
    print("profiler done:", a.prefix)