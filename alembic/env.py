import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool, text
from alembic import context

# ── PYTHONPATH: /app 을 sys.path에 추가 (Docker WORKDIR = /app) ─────────────
# alembic.ini의 prepend_sys_path = . 만으로는 부족한 경우를 대비한 명시적 보장
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# ── 프로젝트 모델 임포트 ──────────────────────────────────────────────────────
from src.core.model import Base  # noqa: E402

# alembic.ini의 로깅 설정 적용
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Alembic이 추적할 메타데이터 (autogenerate 용)
target_metadata = Base.metadata

# ── DB URL을 환경변수에서 동적으로 주입 ────────────────────────────────────────
def get_sync_url() -> str:
    user     = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    host     = os.getenv("DB_CONTAINER", "127.0.0.1")
    port     = os.getenv("POSTGRES_PORT", "5432")
    db       = os.getenv("POSTGRES_DB", "moviedb")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


TARGET_SCHEMA = "movie"


def _include_object(obj, name, type_, reflected, compare_to):
    """
    movie 스키마의 테이블만 추적.
    - type_ == "table" 인 경우: obj.schema 가 TARGET_SCHEMA 인 것만 포함
    - 그 외(index, constraint 등): 모두 포함
    """
    if type_ == "table":
        return obj.schema == TARGET_SCHEMA
    return True


def run_migrations_offline() -> None:
    """마이그레이션 SQL만 생성 (DB 연결 없이)"""
    url = get_sync_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema=TARGET_SCHEMA,
        include_schemas=True,
        include_object=_include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """실제 DB에 마이그레이션 적용"""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_sync_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # movie 스키마 생성 (없을 경우에만)
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {TARGET_SCHEMA}"))
        connection.execute(text(f"SET search_path TO {TARGET_SCHEMA}"))
        connection.commit()

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema=TARGET_SCHEMA,
            include_schemas=True,
            include_object=_include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
