import grpc
import cv2
import os

from protos import inference_pb2 as pb2
from protos import inference_pb2_grpc as pb2_grpc

TARGET = "server_grcp_gpu:50051"

# 📁 Pasta onde estão as imagens
IMAGE_DIR = "/workspaces/Client-Server-gRCP/client/src/img/"

# 🖼️ Nome da imagem a ser testada (mude aqui)
IMAGE_NAME = "test.jpg"


def main():
    image_path = os.path.join(IMAGE_DIR, IMAGE_NAME)

    img = cv2.imread(image_path)
    if img is None:
        print(f"Erro: não consegui abrir a imagem em {image_path}")
        return

    ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    if not ok:
        print("Erro ao converter imagem para JPEG.")
        return

    channel = grpc.insecure_channel(
        TARGET,
        options=[
            ("grpc.max_send_message_length", 64 * 1024 * 1024),
            ("grpc.max_receive_message_length", 64 * 1024 * 1024),
        ],
    )

    stub = pb2_grpc.InferenceServiceStub(channel)

    req = pb2.InferRequest(
        image_bytes=buf.tobytes(),
        confidence_threshold=0.10,
        bbox_format="xywh",
        include_segmentation=False,
    )

    print("\n📡 Chamando Infer() ...\n")
    resp = stub.Infer(req)

    print("===== RETORNO BRUTO =====")
    print(resp)
    print("=========================\n")

    if resp.error:
        print("❌ Erro do servidor:", resp.error)
        return

    color_map = {d.class_id: (d.ui_color.b, d.ui_color.g, d.ui_color.r) for d in resp.defect_list}

    for i, b in enumerate(resp.list_bbox):
        x, y, w, h = int(b.x), int(b.y), int(b.w), int(b.h)
        color = color_map.get(b.class_id, (0, 255, 0))

        cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)
        label = f"{b.label} {b.confidence:.2f}"
        cv2.putText(img, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    if resp.HasField("img_segmentation"):
        with open("seg_overlay.jpg", "wb") as f:
            f.write(resp.img_segmentation)
        print("🧩 Overlay salvo em seg_overlay.jpg")
    else:
        cv2.imwrite("result.jpg", img)
        print("📸 Resultado salvo em result.jpg")

    channel.close()


if __name__ == "__main__":
    main()
