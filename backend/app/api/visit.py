from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.visit import VisitCreate, VisitUpdate, VisitResponse
from app.services.visit_service import VisitService

router = APIRouter(prefix="/visits", tags=["Visits"])


@router.post("", response_model=VisitResponse, status_code=status.HTTP_201_CREATED)
def create_visit(visit_data: VisitCreate, db: Session = Depends(get_db)):
    return VisitService.create_visit(db, visit_data)


@router.get("", response_model=list[VisitResponse])
def get_all_visits(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return VisitService.get_all_visits(db, skip=skip, limit=limit)


@router.get("/{visit_id}", response_model=VisitResponse)
def get_visit_by_id(visit_id: int, db: Session = Depends(get_db)):
    visit = VisitService.get_visit_by_id(db, visit_id)
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    return visit


@router.put("/{visit_id}", response_model=VisitResponse)
def update_visit(visit_id: int, visit_update: VisitUpdate, db: Session = Depends(get_db)):
    visit = VisitService.update_visit(db, visit_id, visit_update)
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    return visit


@router.delete("/{visit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_visit(visit_id: int, db: Session = Depends(get_db)):
    visit = VisitService.delete_visit(db, visit_id)
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
