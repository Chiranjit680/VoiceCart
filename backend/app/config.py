from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # Database settings
    database_hostname: str = Field(default="localhost")
    database_port: str = Field(default="5432")
    database_password: str = Field(default="unlockit")
    database_name: str = Field(default="VoiceCart")
    database_username: str = Field(default="postgres")
    database_url: str = Field(
        default="postgresql+psycopg2://postgres:unlockit@localhost:5432/VoiceCart"
    )
    
    # JWT settings
    secret_key: str = Field(default="your-secret-key-here")
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30)
    
    # Remove redis_url completely if not needed
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()