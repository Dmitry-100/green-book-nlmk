import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from sqlalchemy.orm import Session

from app.auth import require_role
from app.database import get_db
from app.models.observation import Observation, ObservationStatus
from app.models.species import Species, SpeciesGroup
from app.models.user import User, UserRole

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/observations")
def export_observations(
    group: SpeciesGroup | None = None,
    status: ObservationStatus | None = None,
    user: User = Depends(require_role(UserRole.ecologist, UserRole.admin)),
    db: Session = Depends(get_db),
):
    query = db.query(Observation)
    if group:
        query = query.filter(Observation.group == group.value)
    if status:
        query = query.filter(Observation.status == status)
    observations = query.order_by(Observation.created_at.desc()).all()
    species_ids = {obs.species_id for obs in observations if obs.species_id is not None}
    species_by_id: dict[int, str] = {}
    if species_ids:
        species_rows = (
            db.query(Species.id, Species.name_ru, Species.name_latin)
            .filter(Species.id.in_(species_ids))
            .all()
        )
        species_by_id = {
            species_id: f"{name_ru} ({name_latin})"
            for species_id, name_ru, name_latin in species_rows
        }

    wb = Workbook()
    ws = wb.active
    ws.title = "Наблюдения"
    headers = ["ID", "Группа", "Дата", "Статус", "Вид", "Комментарий", "Широта", "Долгота", "Инцидент", "Создано"]
    ws.append(headers)

    for obs in observations:
        species_name = species_by_id.get(obs.species_id, "") if obs.species_id else ""
        ws.append([
            obs.id,
            obs.group,
            obs.observed_at.strftime("%Y-%m-%d %H:%M") if obs.observed_at else "",
            obs.status.value if obs.status else "",
            species_name,
            obs.comment or "",
            "",  # lat — will be extracted from geometry in production
            "",  # lon
            "Да" if obs.is_incident else "Нет",
            obs.created_at.strftime("%Y-%m-%d %H:%M") if obs.created_at else "",
        ])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = (
        f"observations_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}.xlsx"
    )
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
