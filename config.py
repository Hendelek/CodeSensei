from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr

class Settings(BaseSettings):
    telegram_token: SecretStr
    groq_api_key: SecretStr
    db_path: str = "mentor_bot.db"
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

config = Settings()