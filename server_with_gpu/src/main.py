# infra/grpc/server/server.py

import os
import grpc
from concurrent import futures

from protos import inference_pb2_grpc as pb2_grpc
from infra.grpc.inference_methods import InferenceMethods  # ✅ sua classe nova


MAX_MSG = 64 * 1024 * 1024


def main() -> None:
    port = int(os.getenv("GRPC_PORT", "50051"))
    max_workers = int(os.getenv("GRPC_MAX_WORKERS", "8"))

    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=max_workers),
        options=[
            ("grpc.max_send_message_length", MAX_MSG),
            ("grpc.max_receive_message_length", MAX_MSG),
        ],
    )

    # ✅ registra o servicer correto do seu proto (InferenceMethods)
    pb2_grpc.add_InferenceMethodsServicer_to_server(InferenceMethods(), server)

    server.add_insecure_port(f"[::]:{port}")
    server.start()
    print(f"[SERVER] gRPC InferenceMethods started on :{port}")
    server.wait_for_termination()


if __name__ == "__main__":
    main()
