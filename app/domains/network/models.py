from typing import Optional
from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

class Vlan(Base):
    __tablename__ = "vlans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vlan_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    bemerkung: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    subnets: Mapped[list["Subnet"]] = relationship("Subnet", back_populates="vlan", cascade="all, delete-orphan")


class Subnet(Base):
    __tablename__ = "subnets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    network: Mapped[str] = mapped_column(String(45), nullable=False, unique=True) # e.g. 10.0.1.0/24
    gateway: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)     # e.g. 10.0.1.1
    vlan_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("vlans.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    vlan: Mapped[Optional["Vlan"]] = relationship("Vlan", back_populates="subnets")
