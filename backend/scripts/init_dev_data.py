import sys
import uuid
sys.path.insert(0, ".")
from app.db.session import SessionLocal
from app.models.user import User
from app.models.case import Case
from app.models.enums import UserRole, CaseStatus
from app.services.auth import hash_password

db = SessionLocal()
try:
    user = db.query(User).filter_by(email="dev@crimelens.local").first()
    if not user:
        user = User(
            id=uuid.uuid4(),
            name="Developer",
            email="dev@crimelens.local",
            password_hash=hash_password("password"),
            role=UserRole.ADMIN,
        )
        db.add(user)
        
    case = db.query(Case).filter_by(case_number="CL-7E106F4D14B7").first()
    if not case:
        case = Case(
            id=uuid.uuid4(),
            case_number="CL-7E106F4D14B7",
            title="Operation Nightfall",
            description="Demo case for development",
            status=CaseStatus.OPEN,
            created_by=user.id
        )
        db.add(case)
        
    db.commit()
    print("Created dev user (dev@crimelens.local / password) and case (CL-7E106F4D14B7)")
except Exception as e:
    db.rollback()
    print("Error:", e)
finally:
    db.close()
