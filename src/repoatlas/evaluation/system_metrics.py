def percentile(values, p):
    if not values:
        return 0.0
    xs = sorted(values)
    return xs[min(round((len(xs) - 1) * p), len(xs) - 1)]


def system_metrics(latencies):
    return {
        "p50_task_latency": percentile(latencies, 0.5),
        "p95_task_latency": percentile(latencies, 0.95),
        "external_paid_llm_api_cost": 0.0,
    }
