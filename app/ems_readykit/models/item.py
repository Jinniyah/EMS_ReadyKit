"""
models/item.py
Item — defines what is tracked in inventory.
No PHI or patient data. Operational metadata only.
"""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING, List

from sqlalchemy import String, Boolean, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ems_readykit.core.database import Base
from ems_readykit.models.base import TimestampMixin

if TYPE_CHECKING:
    from ems_readykit.models.stock_lot import StockLot
    from ems_readykit.models.par_level import ParLevel
    from ems_readykit.models.check_line_item import CheckLineItem


class ItemCategory(str, enum.Enum):
    MEDICATION = "Medication"
    CONSUMABLE = "Consumable"
    EQUIPMENT  = "Equipment"


class Item(TimestampMixin, Base):
    __tablename__ = "items"

    item_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    category: Mapped[ItemCategory] = mapped_column(
        SAEnum(ItemCategory, native_enum=False), nullable=False
    )
    # Controlled substances apply only to ALS vehicles (enforced at the workflow layer)
    controlled_substance: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    unit_of_measure: Mapped[str] = mapped_column(String(30), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    stock_lots: Mapped[List["StockLot"]] = relationship("StockLot", back_populates="item")
    par_levels: Mapped[List["ParLevel"]] = relationship("ParLevel", back_populates="item")
    check_line_items: Mapped[List["CheckLineItem"]] = relationship(
        "CheckLineItem", back_populates="item"
    )

    def __repr__(self) -> str:
        return f"<Item id={self.item_id} name={self.name!r} category={self.category}>"
