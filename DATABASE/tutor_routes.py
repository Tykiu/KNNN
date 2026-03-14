from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

# Import supabase và hàm kiểm tra quyền từ file main.py của bạn
from main import supabase, check_verified_user

# Tạo Router để nhúng vào main.py
router = APIRouter(prefix="/tutor", tags=["Tutor Mode"])

# ─────────────────────────────────────────────
# SCHEMAS (Mô hình dữ liệu đầu vào)
# ─────────────────────────────────────────────
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
    receiver_id: str
    content: str

# ─────────────────────────────────────────────
# 1. HỆ THỐNG THÔNG BÁO (Tự động)
# ─────────────────────────────────────────────
def send_notification(user_id: str, content: str):
    """Gửi thông báo tự động vào bảng notifications"""
    data = {
        "user_id": user_id,
        "content": content,
        "is_read": False
        # Không cần gửi created_at vì Supabase đã tự động set now() [4]
    }
    supabase.table("notifications").insert(data).execute()

@router.get("/notifications")
def get_my_notifications(current_user_id: str = Depends(check_verified_user)):
    """Lấy danh sách thông báo của người dùng đang đăng nhập"""
    response = supabase.table("notifications").select("*").eq("user_id", current_user_id).order("created_at", desc=True).execute() 
    return response.data

# ─────────────────────────────────────────────
# 2. TÍNH NĂNG LÀM GIA SƯ
# ─────────────────────────────────────────────
@router.post("/become-tutor")
def activate_tutor(data: TutorActivate, current_user_id: str = Depends(check_verified_user)):
    """Đăng ký làm Gia sư (Không cần up thẻ vì đã hack verified)"""
    update_data = {
        "is_tutor": True,
        "subjects_can_teach": data.subjects,
        "birth_year": data.birth_year
        # Bỏ dòng verified: False ở code gốc để giữ nguyên tích xanh [6]
    }
    supabase.table("users").update(update_data).eq("id", current_user_id).execute() 
    return {"message": "Đăng ký làm Gia sư thành công! Bạn có thể bắt đầu nhận lớp."}

# ─────────────────────────────────────────────
# 3. TÍNH NĂNG TÌM GIA SƯ (TẠO & XEM BÀI ĐĂNG)
# ─────────────────────────────────────────────
@router.post("/requests")
def create_tutor_request(data: TutorRequestCreate, current_user_id: str = Depends(check_verified_user)):
    """Đăng yêu cầu tìm gia sư (Tự lấy ID từ token)"""
    req_data = data.dict() # Chuyển schema thành dict
    req_data["user_id"] = current_user_id
    req_data["status"] = "open" # Mặc định bài đăng là open [7]
    
    response = supabase.table("tutor_requests").insert(req_data).execute()
    return {"message": "Tạo yêu cầu tìm gia sư thành công!", "data": response.data}

@router.get("/requests")
def get_all_open_requests(current_user_id: str = Depends(check_verified_user)):
    """Lấy danh sách các bài đăng tìm gia sư đang mở"""
    # Lấy bài đăng mở và tự động kết nối (join) với bảng users để lấy tên, sdt [8]
    response = supabase.table("tutor_requests").select("*, users(name, phone, MSSV, verified, is_tutor)").eq("status", "open").execute() 
    return response.data

# ─────────────────────────────────────────────
# 4. KẾT NỐI (MATCHING) & CHAT
# ─────────────────────────────────────────────
@router.post("/requests/{request_id}/apply")
def apply_to_teach(request_id: str, current_user_id: str = Depends(check_verified_user)):
    """Gia sư nhấn 'Nhận dạy'"""
    # Lấy thông tin bài đăng để biết ai là người tìm gia sư [8]
    req = supabase.table("tutor_requests").select("user_id, subject_id").eq("id", request_id).single().execute() 
    
    # Báo cho học viên biết có người muốn dạy
    send_notification(
        user_id=req.data['user_id'], 
        content=f"Có một gia sư muốn nhận dạy môn {req.data['subject_id']}. Hãy vào Chat để trao đổi!" [8]
    )
    return {"message": "Đã gửi yêu cầu nhận dạy thành công!"}

@router.post("/requests/{request_id}/apply")
def apply_to_teach(request_id: str, current_user_id: str = Depends(check_verified_user)):
    """Gia sư nhấn 'Nhận dạy'"""
    # 1. Lấy thông tin bài đăng để biết ai là người tìm gia sư
    req_response = supabase.table("tutor_requests").select("user_id, subject_id").eq("id", request_id).single().execute()
    
    if not req_response.data:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài đăng!")
        
    owner_id = req_response.data.get("user_id")
    subject = req_response.data.get("subject_id")
    
    # 2. Gọi hàm send_notification (đã được bạn định nghĩa ở trên) để lưu vào database
    message = f"Một gia sư vừa ứng tuyển để nhận dạy môn {subject} của bạn!"
    send_notification(owner_id, message)
    
    return {"message": "Nhận dạy thành công! Đã gửi thông báo đến học viên."}

@router.post("/chat/send")
def send_message(msg: MessageCreate, current_user_id: str = Depends(check_verified_user)):
    """Nhắn tin nội bộ trao đổi"""
    data = msg.dict()
    data["sender_id"] = current_user_id # Ép ID người gửi là ID từ token đăng nhập [9]
    
    response = supabase.table("messages").insert(data).execute() 
    send_notification(msg.receiver_id, "Bạn có tin nhắn mới!")
    return {"status": "Đã gửi tin nhắn!", "data": response.data}