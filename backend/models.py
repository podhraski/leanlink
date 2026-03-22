from datetime import datetime, timezone
from sqlalchemy import String, Integer, Text, Index, Float, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from database import Base

#stores one row per unique institution from the the rankings csv
class Institution(Base):
    __tablename__ = "institutions"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    name_norm: Mapped[str] = mapped_column(Text, nullable=False)
    country: Mapped[str | None] = mapped_column(String(120), nullable=True)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str | None] = mapped_column(String(32), nullable=True)

#indexes to speed up name and country lookups
Index("ix_institutions_name_norm", Institution.name_norm)
Index("ix_institutions_country", Institution.country)


#logs every reconciliation query and its top result
#useful for analysing usage and improving matching in future iterations
class QueryLog(Base):
    __tablename__ = "query_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    country_filter: Mapped[str | None] = mapped_column(String(120), nullable=True)
    top_result_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    top_result_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    top_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    top_match: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    result_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    queried_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
