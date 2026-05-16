from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, text
from sqlalchemy.dialects.mysql import LONGTEXT, TIMESTAMP
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

ID_TYPE = BigInteger().with_variant(Integer, "sqlite")
LONG_TEXT_TYPE = LONGTEXT().with_variant(Text(), "sqlite")
TIMESTAMP_TYPE = TIMESTAMP().with_variant(DateTime(), "sqlite")


class Base(DeclarativeBase):
    pass


class CreatedAtMixin:
    created_at: Mapped[object] = mapped_column(
        TIMESTAMP_TYPE,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=True,
    )


class TimestampMixin(CreatedAtMixin):
    updated_at: Mapped[object] = mapped_column(
        TIMESTAMP_TYPE,
        server_default=text("CURRENT_TIMESTAMP"),
        server_onupdate=text("CURRENT_TIMESTAMP"),
        nullable=True,
    )


class ContextSnapshot(TimestampMixin, Base):
    __tablename__ = "context_snapshots"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    snapshot_type: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(LONG_TEXT_TYPE, nullable=False)
    tags: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)


class ArchitecturalDecision(TimestampMixin, Base):
    __tablename__ = "architectural_decisions"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    decision_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    rationale: Mapped[str | None] = mapped_column(LONG_TEXT_TYPE, nullable=True)
    consequences: Mapped[str | None] = mapped_column(LONG_TEXT_TYPE, nullable=True)
    alternatives: Mapped[str | None] = mapped_column(LONG_TEXT_TYPE, nullable=True)
    status: Mapped[str | None] = mapped_column(String(50), server_default="active", nullable=True)


class Task(TimestampMixin, Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    parent_task_id: Mapped[int | None] = mapped_column(
        ID_TYPE,
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(LONG_TEXT_TYPE, nullable=True)
    status: Mapped[str | None] = mapped_column(String(50), server_default="pending", nullable=True)
    priority: Mapped[str | None] = mapped_column(String(50), server_default="normal", nullable=True)
    assigned_agent: Mapped[str | None] = mapped_column(String(100), nullable=True)


class TaskLog(CreatedAtMixin, Base):
    __tablename__ = "task_logs"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        ID_TYPE,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    log_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    content: Mapped[str | None] = mapped_column(LONG_TEXT_TYPE, nullable=True)


class CommandHistory(CreatedAtMixin, Base):
    __tablename__ = "command_history"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    agent_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    shell_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    command_text: Mapped[str] = mapped_column(LONG_TEXT_TYPE, nullable=False)
    execution_result: Mapped[str | None] = mapped_column(LONG_TEXT_TYPE, nullable=True)
    success_flag: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    error_message: Mapped[str | None] = mapped_column(LONG_TEXT_TYPE, nullable=True)
    correction_applied: Mapped[str | None] = mapped_column(LONG_TEXT_TYPE, nullable=True)


class LessonLearned(CreatedAtMixin, Base):
    __tablename__ = "lessons_learned"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    problem_description: Mapped[str | None] = mapped_column(LONG_TEXT_TYPE, nullable=True)
    solution_description: Mapped[str | None] = mapped_column(LONG_TEXT_TYPE, nullable=True)
    prevention_strategy: Mapped[str | None] = mapped_column(LONG_TEXT_TYPE, nullable=True)


class ProjectConstraint(TimestampMixin, Base):
    __tablename__ = "project_constraints"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    constraint_key: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    constraint_value: Mapped[str | None] = mapped_column(LONG_TEXT_TYPE, nullable=True)


class ContextEmbedding(CreatedAtMixin, Base):
    __tablename__ = "context_embeddings"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    source_table: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_id: Mapped[int | None] = mapped_column(ID_TYPE, nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    embedding_json: Mapped[str | None] = mapped_column(LONG_TEXT_TYPE, nullable=True)


class AgentMemory(TimestampMixin, Base):
    __tablename__ = "agent_memory"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    agent_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    memory_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content: Mapped[str | None] = mapped_column(LONG_TEXT_TYPE, nullable=True)


class FileIndex(TimestampMixin, Base):
    __tablename__ = "file_index"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    file_path: Mapped[str | None] = mapped_column(String(1000), unique=True, nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_processed: Mapped[object | None] = mapped_column(TIMESTAMP_TYPE, nullable=True)
    summary: Mapped[str | None] = mapped_column(LONG_TEXT_TYPE, nullable=True)
    tags: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
