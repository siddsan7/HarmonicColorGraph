from app.core.config import AppSettings


def test_settings_read_database_url_and_demo_fallback():
    settings = AppSettings(
        DATABASE_URL=(
            "postgresql+psycopg://postgres:secret@"
            "db.example.supabase.co:5432/postgres"
        ),
        HCG_ENABLE_DEMO_FALLBACK=True,
    )

    assert settings.database_url.startswith("postgresql+psycopg://")
    assert settings.demo_fallback_enabled is True


def test_settings_default_to_local_sqlite_and_no_demo_fallback():
    settings = AppSettings(_env_file=None)

    assert settings.database_url == "sqlite+pysqlite:///./.tmp/harmonic_color_graph.db"
    assert settings.demo_fallback_enabled is False
