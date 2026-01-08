import os
import zlib
import grpc
import cv2
import numpy as np
import torch
from ultralytics import YOLO

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


def hex_to_rgb_tuple(hex_color: str):
    hex_color = hex_color.lstrip("#")
    return (int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16))


def stable_idx(name: str, n: int) -> int:
    return zlib.crc32(name.strip().lower().encode("utf-8")) % n


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


# =========================
# SERVICER (gRPC)
# =========================
class InferenceMethods(pb2_grpc.InferenceMethodsServicer):
    """
    Entrada: imagem (bytes JPG/PNG) + confidence_threshold
    Saída: bbox XYWH top-left + defect_list + img_segmentation (b"" quando não houver) + error
    """

    def __init__(self):
        self.model_name = os.getenv("MODEL_NAME", "yolo_detect_default")
        self.model_path = os.getenv("MODEL_PATH", "/code/models/main_defect.pt")
        self.imgsz = int(os.getenv("MODEL_IMGSZ", "640"))
        use_gpu = os.getenv("USE_GPU", "true").lower() in ("1", "true", "yes", "y")
        self.device = 0 if (use_gpu and torch.cuda.is_available()) else "cpu"

        if not self.model_path:
            raise RuntimeError("MODEL_PATH não definido no ambiente.")

        self.model = YOLO(self.model_path)

        # nomes das classes do YOLO
        self.names = self.model.model.names  # dict[int,str]

        # UI colors (estáveis por nome)
        # 60 cores UI
        self.colors = [
            "#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#FF00FF", "#00FFFF",
            "#800000", "#008000", "#000080", "#808000", "#800080", "#008080",
            "#C00000", "#00C000", "#0000C0", "#C0C000", "#C000C0", "#00C0C0",
            "#400000", "#004000", "#000040", "#404000", "#400040", "#004040",
            "#FF4500", "#32CD32", "#1E90FF", "#FFD700", "#ADFF2F", "#FF69B4",
            "#8A2BE2", "#5F9EA0", "#DC143C", "#00CED1", "#228B22", "#FF1493",
            "#00BFFF", "#B8860B", "#6A5ACD", "#20B2AA", "#FF8C00", "#9932CC",
            "#8B0000", "#008B8B", "#2E8B57", "#DA70D6", "#FF6347", "#4682B4",
            "#9ACD32", "#8FBC8F", "#00FA9A", "#1E90FF"
        ]
        self.mask_colors = [
            "#000000", "#010101", "#020202", "#030303", "#040404",
            "#050505", "#060606", "#070707", "#080808", "#090909",
            "#0A0A0A", "#0B0B0B", "#0C0C0C", "#0D0D0D", "#0E0E0E",
            "#0F0F0F", "#101010", "#111111", "#121212", "#131313",
            "#141414", "#151515", "#161616", "#171717", "#181818",
            "#191919", "#1A1A1A", "#1B1B1B", "#1C1C1C", "#1D1D1D",
            "#1E1E1E", "#1F1F1F", "#202020", "#212121", "#222222",
            "#232323", "#242424", "#252525", "#262626", "#272727",
            "#282828", "#292929", "#2A2A2A", "#2B2B2B", "#2C2C2C",
            "#2D2D2D", "#2E2E2E", "#2F2F2F", "#303030", "#313131",
            "#323232", "#333333", "#343434", "#353535", "#363636",
            "#373737", "#383838", "#393939", "#3A3A3A", "#3B3B3B"
        ]

        # cache PB2 (monta uma vez)
        self.defect_list_pb2 = self._build_defect_list_pb2()

        print(
            f"[SERVER] Loaded model_name={self.model_name} model_path={self.model_path} "
            f"device={self.device} imgsz={self.imgsz}"
        )

    def _build_defect_list_pb2(self):
        out = []
        for class_id, name in self.names.items():
            name_str = str(name)

            ui_hex = self.colors[stable_idx(name_str, len(self.colors))]
            mk_hex = self.mask_colors[stable_idx(name_str, len(self.mask_colors))]

            ur, ug, ub = hex_to_rgb_tuple(ui_hex)
            mr, mg, mb = hex_to_rgb_tuple(mk_hex)

            out.append(
                dict_defectinfo_to_pb2({
                    "name": name_str,
                    "class_id": int(class_id),
                    "ui_color": {"r": ur, "g": ug, "b": ub},
                    "mask_color": {"r": mr, "g": mg, "b": mb},
                })
            )
        return out

    def Infer(self, request: pb2.InferRequest, context: grpc.ServicerContext) -> pb2.InferResponse:
        try:
            img = decode_image(request.image_bytes)

            conf = float(request.confidence_threshold)
            if conf <= 0:
                conf = 0.10

            results = self.model.predict(
                source=img,
                imgsz=self.imgsz,
                conf=conf,
                device=self.device,
                verbose=False,
            )

            boxes_pb2 = []
            for r in results:
                if r.boxes is None:
                    continue
                for box in r.boxes:
                    cls_id = int(box.cls[0])
                    score = float(box.conf[0])
                    if score < conf:
                        continue

                    label = str(self.names.get(cls_id, f"class_{cls_id}"))

                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    x1, y1, x2, y2 = float(x1), float(y1), float(x2), float(y2)

                    # PADRÃO ÚNICO: XYWH top-left
                    boxes_pb2.append(
                        pb2.BBox(
                            x=x1,
                            y=y1,
                            w=(x2 - x1),
                            h=(y2 - y1),
                            label=label,
                            class_id=cls_id,
                            confidence=score,
                        )
                    )

            resp = pb2.InferResponse(
                model_name=self.model_name,
                list_bbox=boxes_pb2,
                defect_list=self.defect_list_pb2,
                error="",
            )

            # DETECÇÃO: não tem máscara -> sempre retorna vazio (contrato estável)
            resp.img_segmentation = b""
            return resp

        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))

            resp = pb2.InferResponse(
                model_name=self.model_name,
                list_bbox=[],
                defect_list=self.defect_list_pb2,
                error=str(e),
            )
            resp.img_segmentation = b""
            return resp
