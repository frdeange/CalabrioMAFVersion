from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = Field(default="local", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    app_insights_connection_string: str = Field(
        default="", alias="APP_INSIGHTS_CONNECTION_STRING"
    )
    foundry_project_endpoint: str = Field(default="", alias="FOUNDRY_PROJECT_ENDPOINT")
    model_deployment: str = Field(  # Used by workflow.py (PR #20)
        default="gpt-5.2", alias="MODEL_DEPLOYMENT"
    )
    mcp_wfm_url: str = Field(  # Used by workflow.py (PR #20)
        default="http://mcp-wfm:8001", alias="MCP_WFM_URL"
    )
    intent_agent_name: str = Field(  # Used by workflow.py (PR #20)
        default="wfm-intent-classifier", alias="INTENT_AGENT_NAME"
    )
    sql_builder_agent_name: str = Field(  # Used by workflow.py (PR #20)
        default="wfm-sql-builder", alias="SQL_BUILDER_AGENT_NAME"
    )
    query_executor_agent_name: str = Field(  # Used by workflow.py (PR #20)
        default="wfm-query-executor", alias="QUERY_EXECUTOR_AGENT_NAME"
    )
    default_bu_id: str = Field(default="", alias="DEFAULT_BU_ID")
    apim_gateway_url: str = Field(default="", alias="APIM_GATEWAY_URL")


settings = Settings()
