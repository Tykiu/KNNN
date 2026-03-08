from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
import tutor_models as models  
import shutil, os
from tutor_db import SessionLocal, engine  

# Tự động tạo bảng và folder lưu trữ
models.Base.metadata.create_all(bind=engine)
if not os.path.exists("uploads"): os.makedirs("uploads")

app = FastAPI()

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

@app.get("/")
def root():
    return {"message": "Hệ thống Tutor UIT - Backend hoàn tất!"}

# --- QUẢN LÝ HỌC VIÊN (USERS) ---

@app.post("/create-user/")
def create_user(name: str, MSSV: str, email: str, db: Session = Depends(get_db)):
    new_user = models.User(name=name, MSSV=MSSV, email=email)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "Tạo User thành công!", "user_id": new_user.id}

# HÀM XEM DS TẤT CẢ SINH VIÊN
@app.get("/view-users/")
def list_users(db: Session = Depends(get_db)):
    return db.query(models.User).all()

# HÀM XEM CHI TIẾT 1 HỌC VIÊN THEO ID
@app.get("/view-user/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user: raise HTTPException(status_code=404, detail="Không tìm thấy học viên")
    return user

# --- CHỨC NĂNG GIA SƯ ---

@app.post("/become-tutor/{user_id}")
def activate_tutor(user_id: int, subjects: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user: raise HTTPException(status_code=404, detail="User ko tồn tại")
    
    user.is_tutor = True
    user.subjects_can_teach = subjects 
    db.commit()
    return {
        "message": "Đã kích hoạt chế độ Gia sư!",
        "name": user.name,
        "subjects": user.subjects_can_teach
    }

@app.post("/verify-id/{user_id}")
def upload_id(user_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user: raise HTTPException(status_code=404, detail="User ko tồn tại")
    
    path = f"uploads/{user_id}_{file.filename}"
    with open(path, "wb") as f: 
        shutil.copyfileobj(file.file, f)
    
    user.verified = True
    db.commit()
    return {"status": "Đã xác minh thẻ SV!", "path": path}

# --- QUẢN LÝ YÊU CẦU (REQUESTS) ---

@app.post("/create-tutor-request/")
def create_tutor_request(user_id: int, subject: str, mode: str, loc: str, time: str, note: str, db: Session = Depends(get_db)):
    new_req = models.TutorRequest(user_id=user_id, subject=subject, mode=mode, link_or_address=loc, time=time, note=note)
    db.add(new_req)
    db.commit()
    return {"message": "Đã gửi yêu cầu tìm Gia sư thành công!"}

@app.get("/view-tutor-requests/")
def list_requests(db: Session = Depends(get_db)):
    return db.query(models.TutorRequest).all()