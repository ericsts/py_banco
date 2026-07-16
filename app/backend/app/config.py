from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://banco:change-me@localhost:5432/banco"
    pdf_root: str = "/data/pdf"
    upload_root: str = "/data/uploads"

    secret_key: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_days: int = 7

    admin_email: str = "admin@example.com"
    admin_password: str = "change-me"

    retention_days: int = 7
    frontend_origin: str = "http://localhost:5173"

    class Config:
        env_prefix = ""
        case_sensitive = False


settings = Settings()
