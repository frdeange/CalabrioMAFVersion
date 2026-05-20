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
    sql_connection_string: str = Field(
        default="",
        alias="SQL_CONNECTION_STRING",
    )
    sql_managed_identity_client_id: str = Field(
        default="",
        alias="SQL_MANAGED_IDENTITY_CLIENT_ID",
    )
    sql_metadata_schema: str = Field(default="_metadata", alias="SQL_METADATA_SCHEMA")
    sql_query_timeout_seconds: int = Field(
        default=30,
        alias="SQL_QUERY_TIMEOUT_SECONDS",
    )
    sql_row_limit: int = Field(default=1000, alias="SQL_ROW_LIMIT")
    sql_metadata_cache_seconds: int = Field(
        default=900,
        alias="SQL_METADATA_CACHE_SECONDS",
    )


settings = Settings()
