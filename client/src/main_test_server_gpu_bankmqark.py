import time
import grpc
import cv2
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from statistics import mean

from protos import inference_pb2 as pb2
from protos import inference_pb2_grpc as pb2_grpc


# ===== CONFIG =====
TARGET = "server_grcp_gpu:50051"

IMAGE_DIR = "/workspaces/Client-Server-gRCP/client/src/img/"
IMAGE_NAME = "test.jpg"

TOTAL_REQUESTS = 1000      # total de chamadas
CONCURRENCY = 10           # número de threads
TIMEOUT = 4.0             # timeout por RPC (seg)
WARMUP = 50                # warmup calls (não entra nas métricas)

CONFIDENCE = 0.10
BBOX_FORMAT = "xywh"
INCLUDE_SEG = False

MAX_MSG = 64 * 1024 * 1024
# ==================

def percentile(sorted_vals, p: float) -> float:
    if not sorted_vals:
        return 0.0
    idx = int(p * (len(sorted_vals) - 1))
    return sorted_vals[idx]

def load_image_as_jpeg_bytes(image_dir: str, image_name: str, quality: int = 90) -> bytes:
    image_path = os.path.join(image_dir, image_name)
    img = cv2.imread(image_path)
    if img is None:
        raise RuntimeError(f"Não consegui abrir a imagem em {image_path}")

    ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), int(quality)])
    if not ok:
        raise RuntimeError("Falha ao converter imagem para JPEG.")
    return buf.tobytes()


def make_stub():
    channel = grpc.insecure_channel(
        TARGET,
        options=[
            ("grpc.max_send_message_length", MAX_MSG),
            ("grpc.max_receive_message_length", MAX_MSG),
        ],
    )
    stub = pb2_grpc.InferenceServiceStub(channel)
    return channel, stub


def infer_once(stub, req: pb2.InferRequest) -> float:
    t0 = time.perf_counter()
    resp = stub.Infer(req, timeout=TIMEOUT)
    dt = time.perf_counter() - t0

    # se seu server usa resp.error para app-level errors
    if getattr(resp, "error", ""):
        raise RuntimeError(f"Server error field: {resp.error}")

    return dt


def main():
    image_bytes = load_image_as_jpeg_bytes(IMAGE_DIR, IMAGE_NAME)

    req = pb2.InferRequest(
        image_bytes=image_bytes,
        confidence_threshold=float(CONFIDENCE),
        bbox_format=str(BBOX_FORMAT),
        include_segmentation=bool(INCLUDE_SEG),
    )

    # 1) Warmup (com 1 canal/stub)
    warm_channel, warm_stub = make_stub()
    for _ in range(WARMUP):
        infer_once(warm_stub, req)
    warm_channel.close()

    # 2) Benchmark: cada thread cria seu próprio channel+stub (evita contenção)
    latencies = []
    errors = 0

    t_start = time.perf_counter()

    def worker():
        nonlocal errors
        ch, stub = make_stub()
        try:
            dt = infer_once(stub, req)
            return dt
        except Exception:
            # conta erro e devolve None
            return None
        finally:
            ch.close()

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        futures = [pool.submit(worker) for _ in range(TOTAL_REQUESTS)]
        for f in as_completed(futures):
            res = f.result()
            if res is None:
                errors += 1
            else:
                latencies.append(res)

    t_end = time.perf_counter()
    wall = t_end - t_start

    lat_sorted = sorted(latencies)

    ok_reqs = len(latencies)
    total = TOTAL_REQUESTS

    print("\n===== gRPC INFER BENCH =====")
    print(f"Target: {TARGET}")
    print(f"Image: {os.path.join(IMAGE_DIR, IMAGE_NAME)}")
    print(f"Total requests: {total}")
    print(f"Concurrency (threads): {CONCURRENCY}")
    print(f"Timeout: {TIMEOUT}s")
    print(f"Warmup: {WARMUP}")
    print(f"Wall time: {wall:.3f}s")

    print(f"\nSuccess: {ok_reqs}/{total}")
    print(f"Errors: {errors}/{total}")

    if ok_reqs > 0:
        print(f"Throughput (success only): {ok_reqs / wall:.0f} req/s")
        print(f"Avg latency: {mean(latencies) * 1000:.2f} ms")
        print(f"p50 latency: {percentile(lat_sorted, 0.50) * 1000:.2f} ms")
        print(f"p95 latency: {percentile(lat_sorted, 0.95) * 1000:.2f} ms")
        print(f"p99 latency: {percentile(lat_sorted, 0.99) * 1000:.2f} ms")
    else:
        print("Nenhuma requisição bem-sucedida. Verifique conexão/serviço/proto.")


if __name__ == "__main__":
    main()
