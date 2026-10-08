import argparse
import importlib.util
import os
import platform
import subprocess
import sys
import time

READERS = ("process", "local")
SIDES = {"process": "baseline", "local": "comparison"}
LINENO = {"unwind": "none", "resolve": "last"}


def load_bench_module(src):
    spec = importlib.util.spec_from_file_location("unwind_bench", os.path.join(src, "examples", "unwind_bench.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def calibrate(bench, mode, reader, target_s):
    lineno = LINENO[mode]
    n = 16
    while True:
        s = bench.run(mode, reader, lineno, n)
        if s.errors:
            raise AssertionError(f"{mode} {reader}: {s.errors} errors")
        if s.elapsed_ns >= 20e6 or n >= 1 << 30:
            return max(int(n * target_s * 1e9 / s.elapsed_ns), 1)
        n *= 4


def bench_shape(mod, bench, name, depth, shape, args, out):
    def leaf():
        for mode in ("unwind", "resolve"):
            bench_name = f"{mode}-{name}"
            go_name = f"Benchmark{mode.capitalize()}_{name}"
            for reader in READERS:
                side_dir = os.path.join(out, SIDES[reader], bench_name)
                os.makedirs(side_dir, exist_ok=True)
                lineno = LINENO[mode]
                iters = calibrate(bench, mode, reader, args.rep_seconds)
                lines = []
                for _ in range(args.count):
                    s = bench.run(mode, reader, lineno, iters)
                    if s.errors:
                        raise AssertionError(f"{bench_name} {reader}: {s.errors} errors")
                    ns_op = s.elapsed_ns / s.iters
                    lines.append(
                        f"{go_name} {s.iters} {ns_op:.2f} ns/op {ns_op / max(s.frames_per_iter, 1):.3f} ns/frame {s.frames_per_iter} frames/op\n"
                    )
                with open(os.path.join(side_dir, "bench.txt"), "w") as f:
                    f.write(f"goos: {sys.platform}\ngoarch: {platform.machine()}\npkg: py-spy/unwind_bench\n")
                    f.writelines(lines)
                prof_iters = max(int(iters * args.profile_seconds / args.rep_seconds), 1)
                bench.run(mode, reader, lineno, prof_iters, os.path.join(side_dir, "cpu.pprof"))
                svg = os.path.join(side_dir, "cpu.pprof.svg")
                if os.path.exists(svg):
                    os.remove(svg)
                print(f"{bench_name:<28} {reader:<8} {lines[-1].split()[2]:>12} ns/op", flush=True)

    shape(depth, leaf)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--src", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--count", type=int, default=10)
    p.add_argument("--rep-seconds", type=float, default=0.2)
    p.add_argument("--profile-seconds", type=float, default=2.0)
    p.add_argument("--filter", default="")
    args = p.parse_args()

    mod = load_bench_module(args.src)
    lib = os.path.join(args.src, "target", "release", "examples", mod.LIB_NAME)
    sys.setrecursionlimit(10000)
    bench = mod.Bench(lib)
    started = time.gmtime()
    for name, depth, shape in mod.shapes():
        if args.filter in name:
            bench_shape(mod, bench, name, depth, shape, args, args.out)
    finished = time.gmtime()

    fmt = "%Y-%m-%dT%H:%M:%SZ"
    with open(os.path.join(args.out, "status.yaml"), "w") as f:
        f.write(f"started_at: {time.strftime(fmt, started)}\nfinished_at: {time.strftime(fmt, finished)}\n")
    cpu = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string", "hw.logicalcpu"], capture_output=True, text=True).stdout.split("\n")
    with open(os.path.join(args.out, "host.txt"), "w") as f:
        f.write(f"{cpu[0]}\n{cpu[1]}\n{platform.platform()}\nPython {platform.python_version()}\n")


if __name__ == "__main__":
    main()
