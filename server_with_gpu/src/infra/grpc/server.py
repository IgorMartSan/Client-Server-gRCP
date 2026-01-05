from concurrent import futures
import grpc

from infra.grpc.service import CoreService
from protos import service_pb2_grpc


def start_grpc_server():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    service_pb2_grpc.add_CoreServicesServicer_to_server(CoreService(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    print("gRPC running on 50051")
    server.wait_for_termination()
