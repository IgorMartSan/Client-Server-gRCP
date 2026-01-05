import base64
import cv2
import torch
from ultralytics import YOLO


class ModelManagerYolo:
    def __init__(self, model_path: str, imgsz: int = 640, use_gpu: bool = True):
        self.model_path = model_path
        self.imgsz = imgsz
        self.model = YOLO(self.model_path)

        # device: 0 (GPU) ou "cpu"
        self.device = 0 if (use_gpu and torch.cuda.is_available()) else "cpu"

        self.colors = [
            "#FF5733", "#33FF57", "#3357FF", "#FF33A1", "#33FFA1", "#A133FF",
            "#FF9633", "#33FF96", "#9633FF", "#FF333F", "#33FFDA", "#FFDA33",
            "#DA33FF", "#33DAFF", "#FFD733", "#33FF73", "#7333FF", "#FF3370",
            "#70FF33", "#FF7033", "#33FF70", "#3370FF", "#FF33DA", "#DAFF33",
            "#70DAFF", "#DAFF70", "#FF3377", "#7733FF", "#33FF77", "#FF7733",
        ]
        

    def get_all_classes(self):
        # normalmente dict[int,str]
        return self.model.model.names

    def gpu_is_available(self):
        return torch.cuda.is_available()

    def _encode_base64_jpg(self, img, quality: int = 85) -> str:
        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), int(quality)]
        ok, buffer = cv2.imencode(".jpg", img, encode_params)
        if not ok:
            raise RuntimeError("Falha ao codificar imagem em JPG.")
        return base64.b64encode(buffer).decode("utf-8")

    def detect(
        self,
        img,
        confidence_threshold: float = 0.1,
        bbox_format: str = "xyxy",  # "xyxy" (x1,y1,x2,y2) ou "xywh" (x,y,w,h) top-left
        include_image_base64: bool = False,
        jpg_quality: int = 85,
    ):
        """
        Retorna defeitos com bbox em pixels.

        bbox_format:
          - "xyxy": x1,y1,x2,y2
          - "xywh": x,y,w,h (top-left)
        """
        if bbox_format not in ("xyxy", "xywh"):
            raise ValueError("bbox_format deve ser 'xyxy' ou 'xywh'.")

        h, w = img.shape[:2]

        results = self.model.predict(
            source=img,
            imgsz=self.imgsz,
            conf=confidence_threshold,
            device=self.device,
            verbose=False,
        )

        names = self.model.model.names  # dict
        defects = []

        for r in results:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                name = names.get(cls_id, f"class_{cls_id}")

                conf = float(box.conf[0])
                if conf < confidence_threshold:
                    continue

                x1, y1, x2, y2 = box.xyxy[0].tolist()
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

                color_hex = self.colors[cls_id % len(self.colors)]

                if bbox_format == "xyxy":
                    bbox = {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
                else:
                    bbox = {"x": x1, "y": y1, "w": x2 - x1, "h": y2 - y1}

                defects.append(
                    {
                        "name": name,
                        "class_id": cls_id,
                        "confidence": round(conf, 3),
                        "color_hex": color_hex,
                        "bbox": bbox,
                    }
                )

        data = {
            "defects": defects,
            "image_height": h,
            "image_width": w,
            "device": str(self.device),
        }

        if include_image_base64:
            data["image_base64"] = self._encode_base64_jpg(img, quality=jpg_quality)

        return data
