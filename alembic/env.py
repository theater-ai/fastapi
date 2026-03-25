import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool, text
from alembic import context

# PYTHONPATH: /app 을 sys.path에 추가 (Docker WORKDIR = /app)
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# 프로젝트 모델 임포트
from src.core.model import Base  # noqa: E402

# alembic.ini의 로깅 설정 적용
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Alembic이 추적할 메타데이터 (autogenerate 용)
target_metadata = Base.metadata

# DB URL을 환경변수에서 동적으로 주입
def get_sync_url() -> str:
    user     = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    host     = os.getenv("DB_CONTAINER", "127.0.0.1")
    port     = os.getenv("POSTGRES_PORT", "5432")
    db       = os.getenv("POSTGRES_DB", "moviedb")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"

# 마이그레이션 대상 스키마 지정(movie와 chat)
MOVIE_SCHEMA = "movie"
CHAT_SCHEMA = "chat"


def _include_object(obj, name, type_, reflected, compare_to):
    """
    movie, chat 스키마의 테이블만 추적.
    - type_ == "table" 인 경우: obj.schema 가 TARGET_SCHEMA 인 것만 포함
    - 그 외(index, constraint 등): 모두 포함
    """

    # Alembic이 테이블을 추적할 때, obj.schema가 TARGET_SCHEMA에 포함된 경우에만 포함하도록 설정
    if type_ == "table":
        return obj.schema in [MOVIE_SCHEMA, CHAT_SCHEMA]
    
    # 인덱스, 제약조건 등은 모두 포함 (스키마에 상관없이)
    if hasattr(obj, "table") and obj.table is not None:
        return obj.table.schema in [MOVIE_SCHEMA, CHAT_SCHEMA]

    return True


def run_migrations_offline() -> None:
    """마이그레이션 SQL만 생성 (DB 연결 없이)"""
    url = get_sync_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema=MOVIE_SCHEMA,
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
        # movie, chat 스키마 생성 (없을 경우에만)
        for schema in [MOVIE_SCHEMA, CHAT_SCHEMA]:
            connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
        connection.execute(text(f"SET search_path TO {', '.join([MOVIE_SCHEMA, CHAT_SCHEMA])}"))
        connection.commit()

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema=MOVIE_SCHEMA,
            include_schemas=True,
            include_object=_include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
