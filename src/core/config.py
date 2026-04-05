from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    ENVIRONMENT: str = Field(default="development")
    LOG_LEVEL: str = Field(default="INFO")
    AZURE_OPENAI_ENDPOINT: str = Field(default="https://localhost-openai.openai.azure.com/")
    AZURE_OPENAI_API_KEY: str = Field(default="dev-openai-api-key")
    AZURE_OPENAI_DEPLOYMENT: str = Field(default="gpt-4o-mini")
    AZURE_SEARCH_ENDPOINT: str = Field(default="https://localhost-search.search.windows.net")
    AZURE_SEARCH_KEY: str = Field(default="dev-search-key")
    AZURE_SEARCH_INDEX: str = Field(default="architecture-governance-index")
    AZURE_STORAGE_CONNECTION_STRING: str = Field(
        default="UseDevelopmentStorage=true"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
