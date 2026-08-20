from datetime import date
from typing import Optional, Literal
from .common import SchemaBase

class PatientCreate(SchemaBase):
    patient_external_id: str
    first_name: str
    last_name: str
    date_of_birth: Optional[date] = None
    gender: Optional[Literal["male","female","other","unknown"]] = None
    member_id: Optional[str] = None

class PatientUpdate(SchemaBase):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    member_id: Optional[str] = None

class PatientResponse(PatientCreate):
    id: int
