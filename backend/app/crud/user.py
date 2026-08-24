from typing import List, Optional
from sqlalchemy.orm import Session
import bcrypt
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        pwd_bytes = plain.encode("utf-8")[:72]
        return bcrypt.checkpw(pwd_bytes, hashed.encode("utf-8"))
    except Exception:
        return False


def get_user(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    return db.query(User).offset(skip).limit(limit).all()


def create_user(db: Session, user: UserCreate) -> User:
    from app.models.provider import Provider
    from app.models.role import Role
    
    data = user.model_dump()
    data["password_hash"] = hash_password(data.pop("password"))
    data.pop("role", None)
    db_user = User(**data)
    db.add(db_user)
    db.flush()  # Get user.id before commit
    
    # ✅ Auto-create provider record if user role is "provider"
    if db_user.role_id:
        role = db.query(Role).filter(Role.id == db_user.role_id).first()
        if role and role.name.lower() == "provider":
            # Check if provider already exists
            existing_provider = db.query(Provider).filter(
                Provider.user_id == db_user.id
            ).first()
            
            if not existing_provider:
                # Generate unique NPI
                npi = f"9999{str(db_user.id).zfill(6)}"
                
                # Check NPI uniqueness
                npi_exists = db.query(Provider).filter(Provider.npi == npi).first()
                if npi_exists:
                    npi = f"8888{str(db_user.id).zfill(6)}"
                
                provider = Provider(
                    npi=npi,
                    name=db_user.full_name or f"Provider {db_user.id}",
                    provider_type="Facility",
                    specialty="General Practice",
                    tax_id=f"TAX-{db_user.id}",
                    address="",
                    is_active=True,
                    user_id=db_user.id,
                )
                db.add(provider)
                print(f"[AUTO-CREATE] Provider record created for user: {db_user.email}")
    
    db.commit()
    db.refresh(db_user)
    return db_user



def update_user(db: Session, user_id: int, user: UserUpdate) -> Optional[User]:
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    for field, value in user.model_dump(exclude_unset=True).items():
        setattr(db_user, field, value)
    db.commit()
    db.refresh(db_user)
    return db_user


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = get_user_by_email(db, email)
    if not user or not verify_password(password, user.password_hash):
        return None
    return user
