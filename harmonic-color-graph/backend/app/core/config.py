from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = Field(
        default="sqlite+pysqlite:///./.tmp/harmonic_color_graph.db",
        alias="DATABASE_URL",
    )
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


@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()
