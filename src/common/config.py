import os
from dotenv import load_dotenv

load_dotenv()

CONFLUENCE_CFG = {
    "base_url": os.getenv("CONFLUENCE_BASE_URL", "").rstrip("/"),
    "username": os.getenv("CONFLUENCE_USERNAME", ""),
    "api_token": os.getenv("CONFLUENCE_API_TOKEN", ""),
    "context_path": os.getenv("CONFLUENCE_CONTEXT_PATH", "/confluence"),
    "api_version": os.getenv("CONFLUENCE_API_VERSION", "latest"),
    "timeout": int(os.getenv("CONFLUENCE_TIMEOUT", 30)),
}


def set_confluence_config_from_cli(config: dict):
    for key, value in config.items():
        if key in ["timeout"]:
            CONFLUENCE_CFG[key] = int(value)
        elif value is not None:
            CONFLUENCE_CFG[key] = str(value)


def validate_confluence_config() -> tuple[bool, str]:
    required_fields = ["base_url", "username", "api_token"]
    missing_fields = [field for field in required_fields if not CONFLUENCE_CFG[field]]
    if missing_fields:
        return False, f"缺少必要配置项: {', '.join(missing_fields)}"
    return True, ""


def get_api_base_url() -> str:
    context_path = CONFLUENCE_CFG["context_path"].strip("/")
    if context_path:
        return f"{CONFLUENCE_CFG['base_url']}/{context_path}/rest/api/{CONFLUENCE_CFG['api_version']}"
    return f"{CONFLUENCE_CFG['base_url']}/rest/api/{CONFLUENCE_CFG['api_version']}"