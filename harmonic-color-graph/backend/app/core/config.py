from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_CORS_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
)


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = Field(
        default="sqlite+pysqlite:///./.tmp/harmonic_color_graph.db",
        alias="DATABASE_URL",
    )
    database_url_load: str | None = Field(
        default=None,
        alias="DATABASE_URL_LOAD",
    )
    redis_url: str | None = Field(default=None, alias="REDIS_URL")
    hcg_jobs_admin_token: str | None = Field(default=None, alias="HCG_JOBS_ADMIN_TOKEN")
    hcg_artifact_root: str = Field(default="../data/artifacts", alias="HCG_ARTIFACT_ROOT")
    hcg_evaluation_source: str = Field(
        default="../data/samples/mini_corpus.csv", alias="HCG_EVALUATION_SOURCE"
    )
    hcg_env: str = Field(default="development", alias="HCG_ENV")
    hcg_cors_origins: str = Field(default="", alias="HCG_CORS_ORIGINS")
    hcg_corpus_version: str = Field(default="unversioned", alias="HCG_CORPUS_VERSION")
    vercel_git_commit_sha: str = Field(default="dev", alias="VERCEL_GIT_COMMIT_SHA")
    hcg_enable_demo_fallback: bool = Field(
        default=False,
        alias="HCG_ENABLE_DEMO_FALLBACK",
    )
    chordonomicon_source_path: str = Field(
        default="../data/raw/chordonomicon.jsonl",
        alias="CHORDONOMICON_SOURCE_PATH",
    )
    chordonomicon_metrics_output: str = Field(
        default="../data/processed/phase1_quality_metrics.json",
        alias="CHORDONOMICON_METRICS_OUTPUT",
    )

    @property
    def demo_fallback_enabled(self) -> bool:
        return self.hcg_enable_demo_fallback

    @property
    def cors_origins(self) -> list[str]:
        if not self.hcg_cors_origins:
            return list(_DEFAULT_CORS_ORIGINS)
        return [origin.strip() for origin in self.hcg_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()
