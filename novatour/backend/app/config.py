from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # AWS
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_default_region: str = "us-east-1"

    # Nova Models
    nova_sonic_model_id: str = "amazon.nova-2-sonic-v1:0"
    nova_lite_model_id: str = "us.amazon.nova-2-lite-v1:0"
    nova_embeddings_model_id: str = "amazon.nova-2-multimodal-embeddings-v1:0"
    nova_act_api_key: str = ""

    # Google APIs
    google_maps_api_key: str = ""
    google_api_key: str = ""

    # Weather
    openweather_api_key: str = ""

    # Geoapify
    geoapify_api_key: str = ""

    # App
    app_name: str = "NovaTour"
    app_port: int = 8000
    log_level: str = "INFO"
    mock_mode: bool = False

    # Resilience
    tool_retry_attempts: int = 2
    tool_retry_min_wait: float = 0.5
    tool_retry_max_wait: float = 2.0
    tool_timeout: float = 10.0

    # DynamoDB
    dynamodb_sessions_table: str = "novatour-sessions"
    dynamodb_itineraries_table: str = "novatour-itineraries"
    dynamodb_preferences_table: str = "novatour-preferences"

    class Config:
        env_file = str(Path(__file__).resolve().parent.parent.parent / ".env")
        extra = "ignore"


settings = Settings()
