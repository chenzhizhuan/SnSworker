"""仙境Hero 配置。"""
import os


class Config:
    BACKEND_HOST = os.environ.get("BACKEND_HOST", "0.0.0.0")
    BACKEND_PORT = int(os.environ.get("BACKEND_PORT", "8083"))
    BACKEND_DEBUG = os.environ.get("BACKEND_DEBUG", "False").lower() == "true"
    FRONTEND_PORT = int(os.environ.get("FRONTEND_PORT", "8503"))
    FRONTEND_HOST = os.environ.get("FRONTEND_HOST", "localhost")

    @classmethod
    def get_backend_url(cls, include_protocol=True):
        protocol = "http://" if include_protocol else ""
        if os.environ.get("ENVIRONMENT") == "production":
            backend_url = os.environ.get("BACKEND_URL", f"http://localhost:{cls.BACKEND_PORT}")
        else:
            backend_url = f"http://localhost:{cls.BACKEND_PORT}"
        return backend_url if include_protocol else backend_url.replace("http://", "").replace("https://", "")
