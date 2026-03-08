from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import supabase

app = FastAPI(title="Hệ thống UIT Study Buddy")

# 🔗 LINK
URL = "https://YOUR_PROJECT.supabase.co"
KEY = "YOUR_SUPABASE_KEY"
supabase_client = supabase.create_client(URL, KEY)

# --- SCHEMA DỮ LIỆU (Models) ---

class UserCreate(BaseModel):
    name: str
    MSSV: str
    email: str
    phone: str        
    birth_year: int   

class TutorActivate(BaseModel):
    subjects: str
    birth_year: int 

class TutorRequestCreate(BaseModel):
    subject_id: str
    mode: str         # "online" hoặc "offline"
    link_or_address: str 
    time: str 
    note: Optional[str] = None

class MessageCreate(BaseModel):
    sender_id: str
    receiver_id: str
    content: str

# --- 1. HỆ THỐNG THÔNG BÁO (NOTIFICATIONS) ---

def send_notification(user_id: str, content: str):
    """Gửi thông báo tự động vào bảng notifications"""
    data = {
        "user_id": user_id, 
        "content": content, 
        "is_read": False, 
        "created_at": str(datetime.now())
    }
    supabase_client.table("notifications").insert(data).execute()

@app.get("/notifications/{user_id}", tags=["Notifications"])
def get_my_notifications(user_id: str):
    """Lấy danh sách thông báo của người dùng"""
    response = supabase_client.table("notifications").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
    return response.data

# --- 2. QUẢN LÝ NGƯỜI DÙNG & GIA SƯ ---

@app.post("/users", tags=["User"])
def create_user(user: UserCreate):
    """Tạo User mới"""
    response = supabase_client.table("users").insert(user.dict()).execute()
    return {"message": "Tạo User thành công!", "data": response.data[0]}

@app.post("/become-tutor/{user_id}", tags=["Tutor Mode"])
def activate_tutor(user_id: str, data: TutorActivate):
    """Đăng ký làm Gia sư, chờ xác thực thẻ SV"""
    update_data = {
        "is_tutor": True, 
        "subjects_can_teach": data.subjects, 
        "birth_year": data.birth_year, 
        "verified": False
    }
    response = supabase_client.table("users").update(update_data).eq("id", user_id).execute()
    
    name = response.data[0].get("name")
    msg = f"Chào {name} ({data.birth_year})! Hãy upload thẻ SV để xác minh dạy môn: {data.subjects}."
    return {"popup_message": msg, "status": "Waiting for verification"}

@app.post("/upload-id/{user_id}", tags=["Tutor Mode"])
def upload_student_card(user_id: str, file: UploadFile = File(...)):
    """Nút 'Chọn tệp' để upload ảnh thẻ SV lên hệ thống"""
    # Cập nhật trạng thái Verified sau khi nhận file
    supabase_client.table("users").update({"verified": True}).eq("id", user_id).execute()
    send_notification(user_id, f"Đã nhận file {file.filename}. Bạn đã được xác minh Gia sư!")
    return {"message": "Upload thành công!", "file_name": file.filename}

# --- 3. QUẢN LÝ BÀI ĐĂNG & BẢO MẬT ---

@app.get("/tutor-requests", tags=["Requests"])
def get_tutor_requests(viewer_id: str | None = None):
    """Lấy bài đăng & ẩn SĐT bảo mật (090****123)"""
    response = supabase_client.table("tutor_requests").select("*, users(name, phone, verified, is_tutor)").eq("status", "open").execute()
    data = response.data

    is_verified_tutor = False
    if viewer_id:
        viewer = supabase_client.table("users").select("is_tutor, verified").eq("id", viewer_id).single().execute()
        if viewer.data and viewer.data.get("is_tutor") and viewer.data.get("verified"):
            is_verified_tutor = True

    for req in data:
        if not is_verified_tutor:
            phone = req['users']['phone']
            req['users']['phone'] = f"{phone[:3]}****{phone[-3:]}"
    return data

# --- 4. KẾT NỐI (MATCHING) & CHAT ---

@app.post("/tutor-requests/{request_id}/apply", tags=["Matching"])
def apply_to_teach(request_id: str, tutor_id: str):
    """Gia sư nhấn 'Nhận dạy'"""
    req = supabase_client.table("tutor_requests").select("user_id, subject_id").eq("id", request_id).single().execute()
    send_notification(req.data['user_id'], f"Gia sư {tutor_id} muốn dạy môn {req.data['subject_id']}. Hãy vào Chat!")
    return {"message": "Đã gửi yêu cầu!"}

@app.post("/tutor-requests/{request_id}/confirm", tags=["Matching"])
def confirm_match(request_id: str, student_id: str, tutor_id: str):
    """Học viên chốt Gia sư: Đóng bài và hiện SĐT liên lạc Zalo"""
    supabase_client.table("tutor_requests").update({"status": "closed"}).eq("id", request_id).execute()
    send_notification(tutor_id, "Học viên đã xác nhận bạn dạy. Hãy kết bạn Zalo ngay!")
    
    s_phone = supabase_client.table("users").select("phone").eq("id", student_id).single().execute()
    t_phone = supabase_client.table("users").select("phone").eq("id", tutor_id).single().execute()
    return {"student_phone": s_phone.data['phone'], "tutor_phone": t_phone.data['phone']}

@app.post("/chat/send", tags=["Chat"])
def send_message(msg: MessageCreate):
    """Nhắn tin nội bộ trao đổi"""
    data = msg.dict()
    data["created_at"] = str(datetime.now())
    response = supabase_client.table("messages").insert(data).execute()
    send_notification(msg.receiver_id, f"Tin nhắn mới từ {msg.sender_id}")
    return {"status": "Đã gửi!", "data": response.data}