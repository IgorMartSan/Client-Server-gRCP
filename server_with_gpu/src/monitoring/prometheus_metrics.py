from prometheus_client import Counter, Summary

LOOP_ITERATIONS = Counter(
    "loop_iterations_total", "Total loop iterations", ["camera", "stream"]
)
LOOP_ITERATION_TIME = Summary(
    "loop_iteration_seconds", "Loop iteration duration (s)", ["camera", "stream"]
)
