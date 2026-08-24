from sqlalchemy import Column, Integer, String, Date
from app.database import Base


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    patient_external_id = Column(String(100), unique=True, nullable=False, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=True)  # Allow NULL for unknown last names
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(20), nullable=True)
    member_id = Column(String(100), nullable=True)
