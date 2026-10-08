import argparse
import html
import json
import os
import re


def format_ns(ns):
    for scale, unit in ((1e6, "ms"), (1e3, "µs")):
        if ns >= scale:
            return f"{ns / scale:.3g} {unit}"
    return f"{ns:.3g} ns"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--html", required=True)
    p.add_argument("--host", required=True)
    p.add_argument("--status", required=True)
    p.add_argument("--ref", required=True)
    p.add_argument("--commit", required=True)
    args = p.parse_args()

    doc = open(args.html).read()
    site = os.path.dirname(args.html)

    m = re.search(r'(<script type="application/json" id="report-data">)(.*?)(</script>)', doc, re.S)
    data = json.loads(m.group(2))
    for b in data["benchmarks"]:
        for prof in b["profiles"]:
            if prof["name"] != "cpu":
                os.remove(os.path.join(site, prof["file"]))
        b["profiles"] = [prof for prof in b["profiles"] if prof["name"] == "cpu"]
        b["metrics"] = [x for x in b["metrics"] if not x["key"].startswith("profile:")]
        for x in b["metrics"]:
            if x["key"] in ("time/op", "ns/frame"):
                for side in ("baseline", "comparison"):
                    if x.get(side + "Value") is not None:
                        x[side] = format_ns(x[side + "Value"])
    raw = json.dumps(data, separators=(",", ":")).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    doc = doc[: m.start(2)] + raw + doc[m.end(2) :]

    cpu, cores, os_name, py = open(args.host).read().split("\n")[:4]
    status = dict(line.split(": ", 1) for line in open(args.status).read().splitlines())
    e = html.escape
    summary = (
        '<dl class="run-summary">'
        f"<div><dt>Baseline</dt><dd>reader=process<br>remoteprocess::Process, reads via the OS (mach_vm_read / process_vm_readv)</dd></div>"
        f"<div><dt>Comparison</dt><dd>reader=local<br>remoteprocess::LocalProcess, direct in-process memory reads</dd></div>"
        f"<div><dt>Source</dt><dd>{e(args.ref)}<br>{e(args.commit[:12])}</dd></div>"
        f"<div><dt>Host</dt><dd>{e(cpu)}<br>{e(cores)} logical CPUs<br>{e(os_name)}<br>{e(py)}</dd></div>"
        f"<div><dt>Run (UTC)</dt><dd>Started: {e(status['started_at'])}<br>Finished: {e(status['finished_at'])}</dd></div>"
        "</dl>"
    )
    doc = re.sub(r'<dl class="run-summary">.*?</dl>', lambda _: summary, doc, count=1, flags=re.S)
    doc = doc.replace("<title>Macro benchmark report</title>", "<title>py-spy in-process unwind benchmark</title>")
    doc = doc.replace("<h1>Macro benchmark report</h1>", "<h1>py-spy in-process unwind benchmark</h1>")
    intro = (
        "<p>examples/unwind_bench runs inside a CPython 3.12 process and samples the calling thread's own stack. "
        "<b>unwind-*</b> walks the frame chain only (unwind_frames); <b>resolve-*</b> additionally resolves code objects to function, file and last-instruction line (resolve_frames). "
        "Each shape (recursive, distinct, methods, c_boundaries, generators at depth N) is measured with both readers; benchstat compares 10 repetitions of about 0.2s each. "
        "Flamegraphs are pprof-rs CPU profiles (999 Hz, bench thread only) of a separate ~2s run per cell; use the diff view to compare readers.</p>"
    )
    doc = re.sub(r"<p>Benchstat compares benchmark repetitions\..*?</p>", lambda _: intro, doc, count=1, flags=re.S)
    open(args.html, "w").write(doc)


if __name__ == "__main__":
    main()
