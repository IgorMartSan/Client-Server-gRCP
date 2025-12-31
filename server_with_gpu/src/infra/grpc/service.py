import time

from proto import service_pb2, service_pb2_grpc


class CoreService(service_pb2_grpc.CoreServicesServicer):

    def Ping(self, request, context):
        return service_pb2.PingReply(message=f"Pong, {request.name}")

    def Sum(self, request, context):
        return service_pb2.SumReply(result=request.a + request.b)

    def StreamNumbers(self, request, context):
        for i in range(1, request.max + 1):
            yield service_pb2.StreamReply(value=i)
            time.sleep(0.5)
