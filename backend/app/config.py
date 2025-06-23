from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int

    database_hostname: str
    database_port: str
    database_username: str
    database_password: str
    database_name: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()