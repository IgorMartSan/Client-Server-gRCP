import os
from dotenv import load_dotenv

load_dotenv()


def split_env_list(env_name: str, cast_type=str, default=None):
    value = os.getenv(env_name)
    if not value:
        return default if default is not None else []
    try:
        return [cast_type(v.strip()) for v in value.split(",") if v.strip()]
    except ValueError:
        raise ValueError(f"Error casting values of {env_name} to {cast_type}")


class Environment:
    def __init__(self):
        self.CONTAINER_NAME: str = os.getenv("CONTAINER_NAME", "config_module_system")
        self.TZ: str = os.getenv("TZ", "America/Sao_Paulo")


    def __repr__(self) -> str:
        lines = ["\n=== Environment Variables ==="]
        for key, value in self.__dict__.items():
            lines.append(f"{key:<40}: {value}")
        lines.append("=============================\n")
        return "\n".join(lines)


if __name__ == "__main__":
    env = Environment()
    print(env)
