import time
from protos import service_pb2, service_pb2_grpc


class CoreService(service_pb2_grpc.CoreServicesServicer):

    # 1️⃣ Unary
    def Ping(self, request, context):
        return service_pb2.PingReply(
            message=f"Pong, {request.name}"
        )

    # 2️⃣ Server Streaming
    def StreamNumbers(self, request, context):
        for i in range(1, request.max + 1):
            yield service_pb2.StreamReply(value=i)
            time.sleep(0.3)

    # 3️⃣ Client Streaming
    def UploadNumbers(self, request_iterator, context):
        total = 0
        for req in request_iterator:
            total += req.value
        return service_pb2.UploadResult(total=total)

    # 4️⃣ Bidirectional Streaming
    def Chat(self, request_iterator, context):
        for msg in request_iterator:
            yield service_pb2.ChatMessage(text=f"Server received: {msg.text}")
