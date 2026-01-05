import os
import time
import logging
import grpc
import cv2

from protos import inference_pb2 as pb2
from protos import inference_pb2_grpc as pb2_grpc


# =========================
# CONFIG
# =========================
# Você pode apontar para 2 serviços diferentes no docker-compose
TARGET_1 = os.getenv("TARGET_1", "server_grcp_gpu:50051")
TARGET_2 = os.getenv("TARGET_2", "server_grcp_gpu:50051")

IMAGE_DIR = os.getenv("IMAGE_DIR", "/workspaces/Client-Server-gRCP/client/src/img/")
IMAGE_NAME = os.getenv("IMAGE_NAME", "test.jpg")

CONFIDENCE = float(os.getenv("CONFIDENCE", "0.10"))
BBOX_FORMAT = os.getenv("BBOX_FORMAT", "xywh")
INCLUDE_SEG = os.getenv("INCLUDE_SEG", "false").lower() in ("1", "true", "yes", "y")

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


def call_infer(stub: pb2_grpc.InferenceServiceStub, image_bytes: bytes, target_name: str) -> None:
    req = pb2.InferRequest(
        image_bytes=image_bytes,
        confidence_threshold=float(CONFIDENCE),
        bbox_format=str(BBOX_FORMAT),
        include_segmentation=bool(INCLUDE_SEG),
    )

    t0 = time.perf_counter()
    resp = stub.Infer(req, timeout=TIMEOUT_SEC)
    
    dt_ms = (time.perf_counter() - t0) * 1000.0

    # Se o server retornou "error" no payload (seu padrão)
    if getattr(resp, "error", ""):
        logger.error("[%s] Server error payload: %s", target_name, resp.error)
        return

    # OK -> log leve
    logger.info(
        "[%s] OK model=%s bboxes=%d seg=%s latency=%.1fms",
        target_name,
        resp.model_name,
        len(resp.list_bbox),
        "yes" if resp.HasField("img_segmentation") else "no",
        dt_ms,
    )


def safe_call(fn, target_name: str) -> None:
    """
    Se falhar, só loga e continua o loop (não derruba o cliente).
    """
    try:
        fn()
    except grpc.RpcError as e:
        # gRPC-level error (UNAVAILABLE, DEADLINE_EXCEEDED, etc.)
        logger.error("[%s] gRPC error: code=%s details=%s", target_name, e.code(), e.details())
    except Exception as e:
        logger.error("[%s] error: %s", target_name, str(e))


# =========================
# MAIN
# =========================
def main():
    image_bytes = load_image_bytes()

    ch1 = make_channel(TARGET_1)
    ch2 = make_channel(TARGET_2)

    stub1 = pb2_grpc.InferenceServiceStub(ch1)
    stub2 = pb2_grpc.InferenceServiceStub(ch2)

    logger.info("Dual targets: 1=%s | 2=%s", TARGET_1, TARGET_2)
    logger.info("Image: %s/%s | conf=%.2f bbox=%s seg=%s", IMAGE_DIR, IMAGE_NAME, CONFIDENCE, BBOX_FORMAT, INCLUDE_SEG)

    i = 0
    while True:
        i += 1

        # envia para os dois, mas se um falhar só loga
        safe_call(lambda: call_infer(stub1, image_bytes, "MODEL_1"), "MODEL_1")
        safe_call(lambda: call_infer(stub2, image_bytes, "MODEL_2"), "MODEL_2")

        if SLEEP_BETWEEN_LOOPS_SEC > 0:
            time.sleep(SLEEP_BETWEEN_LOOPS_SEC)


if __name__ == "__main__":
    main()
