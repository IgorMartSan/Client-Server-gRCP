import time
import grpc
from protos import service_pb2, service_pb2_grpc


TARGET = "server_grcp:50051"   # ou "localhost:50051"


def test_ping(stub):
    print("\n--- Unary Ping ---")
    resp = stub.Ping(service_pb2.PingRequest(name="Igor"), timeout=3)
    print("Response:", resp.message)


def test_stream_numbers(stub):
    print("\n--- Server Streaming ---")
    for msg in stub.StreamNumbers(service_pb2.StreamRequest(max=5), timeout=5):
        print("Stream ->", msg.value)


def test_upload_numbers(stub):
    print("\n--- Client Streaming ---")

    def generate():
        for i in range(1, 6):
            yield service_pb2.UploadRequest(value=i)
            time.sleep(0.2)

    resp = stub.UploadNumbers(generate(), timeout=5)
    print("Upload result:", resp.total)


def test_chat(stub):
    print("\n--- Bidirectional Streaming ---")

    def generate():
        for i in range(1, 6):
            yield service_pb2.ChatMessage(text=f"Hello {i}")
            time.sleep(0.3)

    for reply in stub.Chat(generate(), timeout=10):
        print("Chat ->", reply.text)


def main():
    channel = grpc.insecure_channel(
        TARGET,
        options=[
            ("grpc.max_send_message_length", 64 * 1024 * 1024),
            ("grpc.max_receive_message_length", 64 * 1024 * 1024),
        ],
    )

    stub = service_pb2_grpc.CoreServicesStub(channel)

    test_ping(stub)
    test_stream_numbers(stub)
    test_upload_numbers(stub)
    test_chat(stub)


if __name__ == "__main__":
    main()
