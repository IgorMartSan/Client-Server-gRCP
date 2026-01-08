import os
import time
import logging
import grpc
import cv2

from protos import inference_pb2 as pb2
from protos import inference_pb2_grpc as pb2_grpc

from google.protobuf.json_format import MessageToDict
# =========================
# CONFIG
# =========================
TARGET_1 = os.getenv("TARGET_1", "server_grcp_gpu:50051")
TARGET_2 = os.getenv("TARGET_2", "server_grcp_gpu:50051")

IMAGE_DIR = os.getenv("IMAGE_DIR", "/workspaces/Client-Server-gRCP/client/src/img/")
IMAGE_NAME = os.getenv("IMAGE_NAME", "test.jpg")

CONFIDENCE = float(os.getenv("CONFIDENCE", "0.10"))

SLEEP_BETWEEN_LOOPS_SEC = float(os.getenv("SLEEP_BETWEEN_LOOPS_SEC", "0.0"))
TIMEOUT_SEC = float(os.getenv("GRPC_TIMEOUT_SEC", "10.0"))

MAX_MSG = 64 * 1024 * 1024


# =========================
# LOG
# =========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("client_dual_infer")


# =========================
# HELPERS
# =========================
def load_image_bytes() -> bytes:
    image_path = os.path.join(IMAGE_DIR, IMAGE_NAME)
    img = cv2.imread(image_path)
    if img is None:
        raise RuntimeError(f"Não consegui abrir a imagem: {image_path}")

    ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    if not ok:
        raise RuntimeError("Falha ao codificar JPEG.")
    return buf.tobytes()


def make_channel(target: str) -> grpc.Channel:
    return grpc.insecure_channel(
        target,
        options=[
            ("grpc.max_send_message_length", MAX_MSG),
            ("grpc.max_receive_message_length", MAX_MSG),
        ],
    )


def _count_any_bboxes(resp) -> int:
    """
    Tenta contar bboxes mesmo que o nome do campo mude.
    Ajuste aqui se você souber o nome exato no proto novo.
    """
    for name in ("list_bbox", "bboxes", "boxes", "detections", "list_detections"):
        if hasattr(resp, name):
            try:
                return len(getattr(resp, name))
            except Exception:
                pass
    return 0


def call_infer(stub: pb2_grpc.InferenceMethodsStub, image_bytes: bytes, target_name: str) -> None:
    # =========================
    # NEW PROTO REQUEST
    # =========================
    req = pb2.InferRequest(
        image_bytes=image_bytes,
        confidence_threshold=float(CONFIDENCE),
    )

    t0 = time.perf_counter()
    resp = stub.Infer(req, timeout=TIMEOUT_SEC)



    print("==== RAW PROTO ====")
    print(MessageToDict(resp, preserving_proto_field_name=True))
    print("===================")

    dt_ms = (time.perf_counter() - t0) * 1000.0

    # Se existir campo "error" no novo proto (seu padrão antigo), respeita
    if hasattr(resp, "error") and getattr(resp, "error", ""):
        logger.error("[%s] Server error payload: %s", target_name, resp.error)
        return

    # model_name (se existir)
    model_name = getattr(resp, "model_name", "unknown")

    # conta bboxes (campo pode ter mudado)
    n_bboxes = _count_any_bboxes(resp)

    # seg (se existir algum campo de mask/imagem segmentada)
    has_seg = False
    for seg_field in ("img_segmentation", "segmentation", "mask", "img_mask"):
        if hasattr(resp, seg_field):
            try:
                # proto3: HasField só funciona pra message/oneof. Se for bytes, getattr já indica.
                val = getattr(resp, seg_field)
                has_seg = val is not None and (not hasattr(resp, "HasField") or resp.HasField(seg_field) or bool(val))
                if has_seg:
                    break
            except Exception:
                pass

    logger.info(
        "[%s] OK model=%s bboxes=%d seg=%s latency=%.1fms",
        target_name,
        model_name,
        n_bboxes,
        "yes" if has_seg else "no",
        dt_ms,
    )


def safe_call(fn, target_name: str) -> None:
    try:
        fn()
    except grpc.RpcError as e:
        logger.error("[%s] gRPC error: code=%s details=%s", target_name, e.code(), e.details())
    except Exception as e:
        logger.error("[%s] error: %s", target_name, str(e))



import numpy as np

def infer_and_parse(stub, image_bytes: bytes, timeout=10.0):
    """
    Retorna:
      {
        model: str,
        latency_ms: float,
        bboxes: list,
        image: np.ndarray | None
      }
    """
    req = pb2.InferRequest(
        image_bytes=image_bytes,
        confidence_threshold=float(CONFIDENCE),
    )

    t0 = time.perf_counter()
    resp = stub.Infer(req, timeout=timeout)
    latency_ms = (time.perf_counter() - t0) * 1000

    payload = MessageToDict(resp, preserving_proto_field_name=True)

    # ===== bboxes =====
    bboxes = (
        payload.get("list_bbox")
        or payload.get("bboxes")
        or payload.get("detections")
        or []
    )

    # ===== image =====
    img = None
    for k in ("img_segmentation", "segmentation", "mask", "img_mask"):
        if k in payload:
            raw = getattr(resp, k)
            if raw:
                nparr = np.frombuffer(raw, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                break

    return {
        "model": payload.get("model_name", "unknown"),
        "latency_ms": latency_ms,
        "bboxes": bboxes,
        "image": img,
    }






# =========================
# MAIN
# =========================
def loop_async(stub1, stub2, image_bytes):
    print("\n====== LOOP ASYNC ======")
    t_loop = time.perf_counter()

    f1 = infer_future(stub1, image_bytes)
    f2 = infer_future(stub2, image_bytes)

    resp1 = f1.result()
    resp2 = f2.result()

    print("MODEL_1 recebeu")
    print("MODEL_2 recebeu")

    dt = (time.perf_counter() - t_loop) * 1000
    print(f"⏱ Tempo total ASYNC: {dt:.1f} ms")


def loop_sync(stub1, stub2, image_bytes):
    print("\n====== LOOP SYNC ======")
    t_loop = time.perf_counter()

    resp1 = stub1.Infer(pb2.InferRequest(image_bytes=image_bytes, confidence_threshold=CONFIDENCE))
    print("MODEL_1 recebeu")

    resp2 = stub2.Infer(pb2.InferRequest(image_bytes=image_bytes, confidence_threshold=CONFIDENCE))
    print("MODEL_2 recebeu")

    dt = (time.perf_counter() - t_loop) * 1000
    print(f"⏱ Tempo total SYNC: {dt:.1f} ms")


def infer_future(stub, image_bytes):
    req = pb2.InferRequest(image_bytes=image_bytes, confidence_threshold=CONFIDENCE)
    return stub.Infer.future(req, timeout=TIMEOUT_SEC)



def main():
    image_bytes = load_image_bytes()

    stub1 = pb2_grpc.InferenceMethodsStub(make_channel(TARGET_1))
    stub2 = pb2_grpc.InferenceMethodsStub(make_channel(TARGET_2))

    while True:
        loop_async(stub1, stub2, image_bytes)
        loop_sync(stub1, stub2, image_bytes)

        time.sleep(2)




if __name__ == "__main__":
    main()
