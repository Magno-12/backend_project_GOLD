from pydantic_settings import BaseSettings
import ldclient
from ldclient.config import Config

class Settings(BaseSettings):
    PROJECT_NAME: str = "Lottery Aggregator"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    LAUNCHDARKLY_SDK_KEY: str

    class Config:
        env_file = ".env"

settings = Settings()

# Initialize LaunchDarkly client
ld_client = ldclient.set_config(Config(settings.LAUNCHDARKLY_SDK_KEY))

def is_feature_enabled(feature_key: str, user: dict) -> bool:
    return ld_client.variation(feature_key, user, False)
