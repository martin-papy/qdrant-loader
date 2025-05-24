# Profiling and Performance Analysis Guide

This guide explains how to profile and monitor the QDrant Loader pipeline to find bottlenecks and optimize performance. It covers CPU and memory profiling, real-time metrics, and interpreting results.

---

## 1. CPU Profiling with py-spy (Recommended)

**py-spy** is a sampling profiler that can attach to a running Python process and generate flamegraphs.

### Install py-spy

```sh
pip install py-spy
```

### Run the Pipeline and Profile

1. Start your ingestion pipeline as usual:

   ```sh
   python -m qdrant_loader.cli.cli ingest ...
   ```

2. In another terminal, find the process ID (PID):

   ```sh
   ps aux | grep qdrant_loader
   ```

3. Run py-spy to generate a flamegraph:

   ```sh
   py-spy record -o profile.svg --pid <PID>
   ```

4. Open `profile.svg` in your browser to see where time is spent.

### Interpreting Results

- The widest bars are the slowest functions.
- Focus optimization on the biggest/widest bars.

---

## 2. CPU Profiling with cProfile (In-Code Profiling)

You can run the pipeline under cProfile to get a detailed breakdown of function calls and timings.

### Usage

- Use the `--profile` flag with the CLI:

  ```sh
  python -m qdrant_loader.cli.cli ingest --profile ...
  ```

- This will save a `profile.out` file.

### Visualize with SnakeViz

```sh
pip install snakeviz
snakeviz profile.out
```

---

## 3. Memory Profiling

### memory_profiler

- Install: `pip install memory_profiler`
- Add `@profile` decorators to functions you want to analyze.
- Run:

  ```sh
  mprof run python -m qdrant_loader.cli.cli ingest ...
  mprof plot
  ```

### tracemalloc (built-in)

- Add `import tracemalloc; tracemalloc.start()` at the top of your script.
- Use `tracemalloc.get_traced_memory()` to inspect memory usage.

---

## 4. Prometheus Metrics (Real-Time Monitoring)

A Prometheus metrics endpoint will be available at `/metrics` (to be added) when running the pipeline. You can scrape this endpoint with Prometheus and visualize metrics in Grafana.

### Exposed Metrics

- Per-stage timings (chunking, embedding, upsert)
- Queue sizes
- Success/error counts
- Resource usage (CPU, memory)

---

## 5. Next Steps After Profiling

- Use flamegraphs or cProfile output to identify slowest functions.
- Optimize or parallelize the biggest bottlenecks.
- Tune worker counts and batch sizes based on findings.
- Use Prometheus metrics for ongoing monitoring.

---

## 6. Helper Scripts and Makefile Targets

- `make profile-pyspy` — Run py-spy and generate a flamegraph
- `make profile-cprofile` — Run with cProfile and save output
- `make metrics` — Start the Prometheus metrics endpoint

(These will be added to the Makefile and scripts directory.)

---

For questions or help interpreting results, contact the engineering team or see the README for more details.
