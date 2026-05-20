from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = Field(default="local", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    app_insights_connection_string: str = Field(
        default="", alias="APP_INSIGHTS_CONNECTION_STRING"
    )
    mcp_wfm_port: int = Field(default=8001, alias="MCP_WFM_PORT")


settings = Settings()
