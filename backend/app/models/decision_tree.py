from sqlalchemy import String, Integer, ForeignKey, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DecisionTreeNode(Base):
    __tablename__ = "decision_tree"

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("decision_tree.id"), index=True
    )
    question_text: Mapped[str] = mapped_column(Text)
    group: Mapped[str] = mapped_column(String(50))
    suggested_species_ids: Mapped[list[int] | None] = mapped_column(ARRAY(Integer))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
