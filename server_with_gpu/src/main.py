import time
import grpc
from concurrent.futures import ThreadPoolExecutor, as_completed
from statistics import mean
from proto import service_pb2, service_pb2_grpc

TARGET = "server_grcp:50051"   # ou "localhost:50051"

TOTAL_REQUESTS = 5000
CONCURRENCY = 50
TIMEOUT = 5.0

MAX_MSG = 64 * 1024 * 1024


def percentile(sorted_vals, p: float) -> float:
    if not sorted_vals:
        return 0.0
    idx = int(p * (len(sorted_vals) - 1))
    return sorted_vals[idx]


def bench_unary_ping(stub):
    """1 request -> 1 response"""
    t0 = time.perf_counter()
    stub.Ping(service_pb2.PingRequest(name="perf"), timeout=TIMEOUT)
    return time.perf_counter() - t0


def bench_client_streaming(stub, n=50):
    """N requests -> 1 response"""
    def gen():
        for i in range(n):
            yield service_pb2.UploadRequest(value=i)

    t0 = time.perf_counter()
    stub.UploadNumbers(gen(), timeout=TIMEOUT)
    return time.perf_counter() - t0


def bench_server_streaming(stub, n=50):
    """1 request -> N responses"""
    t0 = time.perf_counter()
    for _ in stub.StreamNumbers(service_pb2.StreamRequest(max=n), timeout=TIMEOUT):
        pass
    return time.perf_counter() - t0


def run_bench(name, fn, stub):
    # Warmup
    for _ in range(50):
        fn(stub)

    latencies = []
    t_start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        futures = [pool.submit(fn, stub) for _ in range(TOTAL_REQUESTS)]
        for f in as_completed(futures):
            latencies.append(f.result())

    t_end = time.perf_counter()
    wall = t_end - t_start

    lat_sorted = sorted(latencies)

    print(f"\n=== {name} ===")
    print(f"Target: {TARGET}")
    print(f"Requests: {TOTAL_REQUESTS}")
    print(f"Concurrency: {CONCURRENCY}")
    print(f"Wall time: {wall:.3f}s")
    print(f"Throughput: {TOTAL_REQUESTS / wall:.0f} req/s")
    print(f"Avg latency: {mean(latencies) * 1000:.2f} ms")
    print(f"p50 latency: {percentile(lat_sorted, 0.50) * 1000:.2f} ms")
    print(f"p95 latency: {percentile(lat_sorted, 0.95) * 1000:.2f} ms")
    print(f"p99 latency: {percentile(lat_sorted, 0.99) * 1000:.2f} ms")


def main():
    channel = grpc.insecure_channel(
        TARGET,
        options=[
            ("grpc.max_send_message_length", MAX_MSG),
            ("grpc.max_receive_message_length", MAX_MSG),
        ],
    )
    stub = service_pb2_grpc.CoreServicesStub(channel)

    # 1) Melhor métrica de “RPC puro”
    run_bench("Unary Ping", bench_unary_ping, stub)

    # 2) Client-streaming (simula upload/chunks/batch)
    run_bench("Client Streaming UploadNumbers (50 msgs)", lambda s: bench_client_streaming(s, n=50), stub)

    # 3) Server-streaming (simula results/progress/logs)
    run_bench("Server Streaming StreamNumbers (50 msgs)", lambda s: bench_server_streaming(s, n=50), stub)

    channel.close()


if __name__ == "__main__":
    main()
