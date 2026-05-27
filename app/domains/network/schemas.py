from typing import Optional
from pydantic import BaseModel, ConfigDict


class VlanBase(BaseModel):
    vlan_id: int
    name: str
    bemerkung: Optional[str] = None


class VlanResponse(VlanBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class SubnetBase(BaseModel):
    network: str
    gateway: Optional[str] = None
    vlan_id: Optional[int] = None


class SubnetResponse(SubnetBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
