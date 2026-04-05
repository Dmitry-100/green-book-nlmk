import io
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from sqlalchemy.orm import Session

from app.auth import require_role
from app.database import get_db
from app.models.observation import Observation, ObservationStatus
from app.models.species import Species
from app.models.user import User, UserRole

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/observations")
def export_observations(
    group: str | None = None,
    status: ObservationStatus | None = None,
    user: User = Depends(require_role(UserRole.ecologist, UserRole.admin)),
    db: Session = Depends(get_db),
):
    query = db.query(Observation)
    if group:
        query = query.filter(Observation.group == group)
    if status:
        query = query.filter(Observation.status == status)
    observations = query.order_by(Observation.created_at.desc()).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Наблюдения"
    headers = ["ID", "Группа", "Дата", "Статус", "Вид", "Комментарий", "Широта", "Долгота", "Инцидент", "Создано"]
    ws.append(headers)

    for obs in observations:
        species_name = ""
        if obs.species_id:
            sp = db.query(Species).filter(Species.id == obs.species_id).first()
            species_name = f"{sp.name_ru} ({sp.name_latin})" if sp else ""
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

    filename = f"observations_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
