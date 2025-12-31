from config.logger import setup_logger, logging
from infra.grpc.server import start_grpc_server
from infra.env.environment import Environment

def main():
    env = Environment()
    setup_logger(container_name=env.CONTAINER_NAME, show_log=True)
    logger = logging.getLogger()
    logger.info("Booting gRPC server...")
    start_grpc_server()

if __name__ == "__main__":
    main()
