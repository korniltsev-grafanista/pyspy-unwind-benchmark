# py-spy in-process unwind benchmark

Report: https://korniltsev-grafanista.github.io/pyspy-unwind-benchmark/

Compares py-spy stack unwinding and frame resolution inside a CPython 3.12 process using the out-of-process reader (`remoteprocess::Process`) as baseline and the in-process reader (`remoteprocess::LocalProcess`) as comparison. The page is rendered with the `report` command of the [pyroscope macro-benchmark tool](https://github.com/simonswine/pyroscope/tree/macro-benchmark/tools/macro-benchmark).

`scripts/run.py` drives `examples/unwind_bench` and writes benchstat-format results and pprof CPU profiles; `scripts/build.sh` packs them into the macro-benchmark archive layout, renders the report and adapts its summary with `scripts/postprocess.py`.
