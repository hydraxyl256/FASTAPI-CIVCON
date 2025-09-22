from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_hostname: str
    database_url: str
    database_password:str
    database_name: str
    database_username: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    google_client_id: str
    google_client_secret: str
    linkedin_client_id: str
    linkedin_client_secret: str

    model_config = SettingsConfigDict(
        env_file=".env",  
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
settings = Settings()

