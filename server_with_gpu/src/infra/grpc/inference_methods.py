import os
import grpc
import cv2
import numpy as np

from model_manager_yolo import ModelManagerYolo
from protos import inference_pb2 as pb2
from protos import inference_pb2_grpc as pb2_grpc


# =========================
# HELPERS
# =========================
def decode_image(image_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Imagem inválida. Envie JPEG/PNG válido.")
    return img


def dict_defectinfo_to_pb2(d: dict) -> pb2.DefectInfo:
    return pb2.DefectInfo(
        name=str(d["name"]),
        class_id=int(d["class_id"]),
        ui_color=pb2.RGB(
            r=int(d["ui_color"]["r"]),
            g=int(d["ui_color"]["g"]),
            b=int(d["ui_color"]["b"]),
        ),
        mask_color=pb2.RGB(
            r=int(d["mask_color"]["r"]),
            g=int(d["mask_color"]["g"]),
            b=int(d["mask_color"]["b"]),
        ),
    )


def dict_bbox_to_pb2(b: dict) -> pb2.BBox:
    return pb2.BBox(
        x=float(b["x"]),
        y=float(b["y"]),
        w=float(b["w"]),
        h=float(b["h"]),
        label=str(b.get("label", "")),
        class_id=int(b.get("class_id", -1)),
        confidence=float(b.get("confidence", 0.0)),
    )


# =========================
# SERVICER (gRPC)
# =========================
class InferenceMethods(pb2_grpc.InferenceMethodsServicer):
    """
    Implementa o service do proto:

      service InferenceMethods {
        rpc Infer(InferRequest) returns (InferResponse);
      }
    """

    def __init__(self):
        self.model_name = os.getenv("MODEL_NAME", "yolo_detect_default")
        self.model_path = os.getenv("MODEL_PATH", "/code/models/main_defect.pt")
        imgsz = int(os.getenv("MODEL_IMGSZ", "640"))
        use_gpu = os.getenv("USE_GPU", "true").lower() in ("1", "true", "yes", "y")

        if not self.model_path:
            raise RuntimeError("MODEL_PATH não definido no ambiente.")

        self.model = ModelManagerYolo(self.model_path, imgsz=imgsz, use_gpu=use_gpu)

        # pega do cache do próprio model (já vem cores por NOME)
        self.defect_list_pb2 = [
            dict_defectinfo_to_pb2(d) for d in getattr(self.model, "_defect_list_cached", [])
        ]

        print(
            f"[SERVER] Loaded model_name={self.model_name} "
            f"model_path={self.model_path} device={getattr(self.model, 'device', 'unknown')}"
        )

    def Infer(self, request: pb2.InferRequest, context: grpc.ServicerContext) -> pb2.InferResponse:
        try:
            img = decode_image(request.image_bytes)

            request_like = {
                "confidence_threshold": float(request.confidence_threshold),
                "bbox_format": str(request.bbox_format),
                "include_segmentation": bool(request.include_segmentation),
            }

            out = self.model.infer_proto_like(img, request_like)

            boxes_pb2 = [dict_bbox_to_pb2(b) for b in out.get("list_bbox", [])]

            resp = pb2.InferResponse(
                model_name=str(out.get("model_name", self.model_name)),
                list_bbox=boxes_pb2,
                defect_list=self.defect_list_pb2,
                error=str(out.get("error", "")),
            )

            seg = out.get("img_segmentation", None)
            if seg is not None:
                resp.img_segmentation = seg  # bytes

            return resp

        except Exception as e:
            # gRPC error (nível protocolo)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))

            # payload error (seu padrão)
            return pb2.InferResponse(
                model_name=self.model_name,
                defect_list=self.defect_list_pb2,
                error=str(e),
            )
