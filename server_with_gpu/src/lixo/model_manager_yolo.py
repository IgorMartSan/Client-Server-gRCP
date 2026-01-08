import os
import zlib
import torch
from ultralytics import YOLO


def hex_to_rgb_tuple(hex_color: str):
    hex_color = hex_color.lstrip("#")
    return (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16),
    )


def norm_name(name: str) -> str:
    # garante estabilidade mesmo se vier "Scratch" vs "scratch "
    return name.strip().lower()


def stable_idx(name: str, n: int) -> int:
    # determinístico: mesmo nome => mesmo índice
    return zlib.crc32(norm_name(name).encode("utf-8")) % n


class ModelManagerYolo:
    def __init__(self, model_path: str, imgsz: int = 640, use_gpu: bool = True):
        self.model_path = model_path
        self.imgsz = imgsz
        self.model = YOLO(self.model_path)
        self.device = 0 if (use_gpu and torch.cuda.is_available()) else "cpu"

        # UI (bbox/texto)
        self.colors = [
            "#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#FF00FF", "#00FFFF",
            "#800000", "#008000", "#000080", "#808000", "#800080", "#008080",
            "#C00000", "#00C000", "#0000C0", "#C0C000", "#C000C0", "#00C0C0",
            "#400000", "#004000", "#000040", "#404000", "#400040", "#004040",
            "#FF4500", "#32CD32", "#1E90FF", "#FFD700", "#ADFF2F", "#FF69B4",
            "#8A2BE2", "#5F9EA0", "#DC143C", "#00CED1", "#228B22", "#FF1493",
            "#00BFFF", "#B8860B", "#6A5ACD", "#20B2AA", "#FF8C00", "#9932CC",
            "#8B0000", "#008B8B", "#2E8B57", "#DA70D6", "#FF6347", "#4682B4",
            "#9ACD32", "#8FBC8F", "#00FA9A", "#1E90FF", "#FF4500", "#DAA520",
            "#7FFF00", "#40E0D0", "#BA55D3", "#F08080", "#00FF7F", "#CD5C5C",
            "#87CEFA", "#32CD32", "#66CDAA", "#EE82EE", "#4682B4", "#BDB76B"
        ]

        # Máscara (grayscale-friendly / contínuo)
        self.mask_colors = [
            "#0A0A0A", "#141414", "#1E1E1E", "#282828", "#323232",
            "#3C3C3C", "#464646", "#505050", "#5A5A5A", "#646464",
            "#6E6E6E", "#787878", "#828282", "#8C8C8C", "#969696",
            "#A0A0A0", "#AAAAAA", "#B4B4B4", "#BEBEBE", "#C8C8C8",
            "#D2D2D2", "#DCDCDC", "#E6E6E6", "#F0F0F0", "#FAFAFA",
            "#0F0F0F", "#191919", "#232323", "#2D2D2D", "#373737",
            "#414141", "#4B4B4B", "#555555", "#5F5F5F", "#696969",
            "#737373", "#7D7D7D", "#878787", "#919191", "#9B9B9B",
            "#A5A5A5", "#AFAFAF", "#B9B9B9", "#C3C3C3", "#CDCDCD",
            "#D7D7D7", "#E1E1E1", "#EBEBEB", "#F5F5F5", "#FFFFFF",
            "#121212", "#1C1C1C", "#262626", "#303030", "#3A3A3A",
            "#444444", "#4E4E4E", "#585858", "#626262", "#6C6C6C",
            "#767676", "#808080", "#8A8A8A", "#949494", "#9E9E9E",
        ]

        # ✅ Cache do defect_list (monta uma vez só)
        self._defect_list_cached = self.build_defect_list_proto_like()

    def get_all_classes(self):
        return self.model.model.names

    def build_defect_list_proto_like(self):
        """
        Agora: ui_color e mask_color são escolhidos pelo NOME (estável entre versões).
        class_id continua sendo o do modelo (YOLO). (Se quiser também estabilizar, eu ajusto.)
        """
        defect_list = []
        names = self.get_all_classes()  # dict[int,str]

        for class_id, name in names.items():
            name_str = str(name)

            ui_hex = self.colors[stable_idx(name_str, len(self.colors))]
            mk_hex = self.mask_colors[stable_idx(name_str, len(self.mask_colors))]

            ur, ug, ub = hex_to_rgb_tuple(ui_hex)
            mr, mg, mb = hex_to_rgb_tuple(mk_hex)

            defect_list.append({
                "name": name_str,
                "class_id": int(class_id),  # mantém ID do YOLO (compatibilidade)
                "ui_color": {"r": ur, "g": ug, "b": ub},
                "mask_color": {"r": mr, "g": mg, "b": mb},
            })

        return defect_list

    def infer_proto_like(self, img, request_like: dict):
        try:
            conf = float(request_like.get("confidence_threshold", 0.0))
            if conf <= 0:
                conf = 0.10

            bbox_format = request_like.get("bbox_format") or "xywh"
            if bbox_format not in ("xywh", "xyxy"):
                bbox_format = "xywh"

            results = self.model.predict(
                source=img,
                imgsz=self.imgsz,
                conf=conf,
                device=self.device,
                verbose=False,
            )

            names = self.get_all_classes()
            list_bbox = []

            for r in results:
                for box in r.boxes:
                    cls_id = int(box.cls[0])
                    label = str(names.get(cls_id, f"class_{cls_id}"))

                    score = float(box.conf[0])
                    if score < conf:
                        continue

                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    x1, y1, x2, y2 = float(x1), float(y1), float(x2), float(y2)

                    # ✅ Sempre retorna XYWH top-left
                    x = x1
                    y = y1
                    w = (x2 - x1)
                    h = (y2 - y1)

                    list_bbox.append({
                        "x": x,
                        "y": y,
                        "w": w,
                        "h": h,
                        "label": label,
                        "class_id": cls_id,
                        "confidence": score,
                    })

            model_name = os.getenv("MODEL_NAME", "yolo_detect_default")

            return {
                "model_name": model_name,
                "list_bbox": list_bbox,
                "img_segmentation": None,            # DETECTION
                "defect_list": self._defect_list_cached,  # ✅ cache + cores por nome
                "error": "",
            }

        except Exception as e:
            return {
                "model_name": os.getenv("MODEL_NAME", "yolo_detect_default"),
                "list_bbox": [],
                "img_segmentation": None,
                "defect_list": self._defect_list_cached,  # útil pro client mesmo em erro
                "error": str(e),
            }
