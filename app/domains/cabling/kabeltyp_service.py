from typing import Mapping, Sequence

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.cabling.models import Cable as CableModel
from app.domains.cabling.models import Kabeltyp as KabeltypModel
from app.domains.cabling.schemas import KabeltypCreate, KabeltypUpdate


GESPERRT_BEI_VERWENDUNG = ("alt_typ", "enden_a", "enden_b")


async def kabeltyp_ids_nach_name(db: AsyncSession) -> dict[str, int]:
    """Katalog als Name → id, für Schreibwege ohne Katalogauswahl (CSV, EPLAN)."""
    result = await db.execute(select(KabeltypModel.name, KabeltypModel.id))
    return {name: kabeltyp_id for name, kabeltyp_id in result.all()}


def kabeltyp_id_nach_typ(
    neuer_typ: str,
    ids_nach_name: Mapping[str, int],
    *,
    alter_typ: str | None = None,
    alte_kabeltyp_id: int | None = None,
) -> int | None:
    """Kabeltyp zu einem typ-String, gleiche Regel wie CablingService beim Ändern.

    Ein gesetzter Kabeltyp bleibt, solange sich typ nicht ändert. Sonst würde ein
    Breakout (alt_typ "sonstige") beim erneuten Import auf die Katalogzeile
    "sonstige" umgebogen. Ohne passende Katalogzeile bleibt das Kabel ohne Typ.
    """
    if alte_kabeltyp_id is not None and neuer_typ == alter_typ:
        return alte_kabeltyp_id
    return ids_nach_name.get(neuer_typ)


class KabeltypService:
    """Pflege des Kabeltyp-Katalogs."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_kabeltypen(
        self, aktiv: bool | None = None
    ) -> Sequence[KabeltypModel]:
        query = select(KabeltypModel).order_by(KabeltypModel.id)
        if aktiv is not None:
            query = query.where(KabeltypModel.aktiv.is_(aktiv))
        return (await self.db.execute(query)).scalars().all()

    async def get_kabeltyp(self, kabeltyp_id: int) -> KabeltypModel:
        kabeltyp = await self.db.get(KabeltypModel, kabeltyp_id)
        if kabeltyp is None:
            raise HTTPException(status_code=404, detail="Kabeltyp nicht gefunden")
        return kabeltyp

    async def create_kabeltyp(self, kabeltyp_in: KabeltypCreate) -> KabeltypModel:
        await self._pruefe_name_frei(kabeltyp_in.name)
        kabeltyp = KabeltypModel(**kabeltyp_in.model_dump())
        self.db.add(kabeltyp)
        await self.db.commit()
        await self.db.refresh(kabeltyp)
        return kabeltyp

    async def update_kabeltyp(
        self, kabeltyp_id: int, kabeltyp_in: KabeltypUpdate
    ) -> KabeltypModel:
        kabeltyp = await self.get_kabeltyp(kabeltyp_id)
        # Nicht gesendete Felder und explizites null bei Pflichtfeldern bleiben unverändert;
        # nur standard_farbe darf geleert werden.
        update_data = {
            feld: wert
            for feld, wert in kabeltyp_in.model_dump(exclude_unset=True).items()
            if wert is not None or feld == "standard_farbe"
        }

        neuer_name = update_data.get("name")
        if neuer_name is not None and neuer_name != kabeltyp.name:
            await self._pruefe_name_frei(neuer_name)

        # alt_typ steht als typ an jedem Kabel, enden_a/enden_b bestimmen die Stränge.
        # Solange Kabel den Typ verwenden, würden diese Änderungen sie inkonsistent machen.
        gesperrt = [
            feld
            for feld in GESPERRT_BEI_VERWENDUNG
            if feld in update_data and update_data[feld] != getattr(kabeltyp, feld)
        ]
        if gesperrt:
            anzahl = await self._anzahl_kabel(kabeltyp.id)
            if anzahl:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"{', '.join(gesperrt)} von Kabeltyp '{kabeltyp.name}' kann "
                        f"nicht geändert werden: {anzahl} Kabel verwenden ihn"
                    ),
                )

        for feld, wert in update_data.items():
            setattr(kabeltyp, feld, wert)
        await self.db.commit()
        await self.db.refresh(kabeltyp)
        return kabeltyp

    async def delete_kabeltyp(self, kabeltyp_id: int) -> None:
        kabeltyp = await self.get_kabeltyp(kabeltyp_id)
        anzahl = await self._anzahl_kabel(kabeltyp.id)
        if anzahl:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Kabeltyp '{kabeltyp.name}' wird von {anzahl} Kabel(n) verwendet "
                    "und kann nicht gelöscht werden. Deaktivieren ist möglich."
                ),
            )
        await self.db.delete(kabeltyp)
        await self.db.commit()

    async def _anzahl_kabel(self, kabeltyp_id: int) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(CableModel)
            .where(CableModel.kabeltyp_id == kabeltyp_id)
        )
        return int(result.scalar_one())

    async def _pruefe_name_frei(self, name: str) -> None:
        result = await self.db.execute(
            select(KabeltypModel.id).where(KabeltypModel.name == name)
        )
        if result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=409, detail=f"Kabeltyp '{name}' existiert bereits"
            )
