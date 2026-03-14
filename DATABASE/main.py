from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional
import os

# Cấu hình Supabase Client
from supabase import create_client, Client

SUPABASE_URL = "https://zfpfyuyegzzzvyxfdwxe.supabase.co"
SUPABASE_KEY = "sb_publishable_BjTxFCgyowtn3AeNXN56sg_cw_9dDIP"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="Study Buddy Auth API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security_scheme = HTTPBearer()

def get_current_token(credentials: HTTPAuthorizationCredentials = Depends(security_scheme)):
    return credentials.credentials

### ─────────────────────────────────────────────
### Schemas (Pydantic)
### ─────────────────────────────────────────────
KHOA = [
    "Khoa học máy tính", "Công nghệ phần mềm", "Khoa học và kỹ thuật thông tin",
    "Hệ thống thông tin", "Kỹ thuật máy tính", "Mạng máy tính và truyền thông",
]

class RegisterRequest(BaseModel):
    name: str  # Cần thiết cho bảng users
    email: EmailStr
    mssv: str
    password: str
    confirm_password: str
    ngay_sinh: int
    thang_sinh: int
    nam_sinh: int
    khoa: str

class LoginRequest(BaseModel):
    email_or_mssv: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

### ─────────────────────────────────────────────
### Routes
### ─────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "Auth API đang chạy 🚀"}

@app.get("/auth/khoa")
def danh_sach_khoa():
    return {"khoa": KHOA}

@app.post("/auth/register", status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest):
    if data.password != data.confirm_password:
        raise HTTPException(status_code=400, detail="Mật khẩu không khớp")

    # 1. Đăng ký qua hệ thống Supabase Authentication [1]
    try:
        auth_response = supabase.auth.sign_up({
            "email": data.email,
            "password": data.password
        })
        user_id = auth_response.user.id
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Lỗi đăng ký Auth: {str(e)}")

    # 2. Thêm thông tin sinh viên vào bảng public.users [2]
    try:
        user_data = {
            "id": user_id,            # Đồng bộ ID từ hệ thống Auth ẩn
            "name": data.name,
            "mssv": data.mssv.upper(),
            "email": data.email,
            "birth_year": data.nam_sinh,
            "verified": False,
            "is_tutor": False,
        }
        supabase.table("users").insert(user_data).execute()
    except Exception as e:
        # Nếu lưu vào bảng users thất bại, có thể gọi code để xoá auth user (fallback)
        raise HTTPException(status_code=400, detail=f"Lỗi lưu hồ sơ: {str(e)}")

    return {"message": "Đăng ký thành công! Vui lòng kiểm tra email để xác thực."}

@app.post("/auth/login", response_model=TokenResponse)
def login(data: LoginRequest):
    email_login = data.email_or_mssv

    # BƯỚC 1: Xử lý nếu người dùng nhập MSSV (chuỗi không chứa ký tự @)
    if "@" not in email_login:
        # Tìm email tương ứng với mssv trong bảng users [2]
        response = supabase.table("users").select("email").eq("mssv", email_login).execute()
        
        # Nếu mảng data rỗng tức là không tìm thấy MSSV
        if len(response.data) == 0:
            raise HTTPException(status_code=400, detail="MSSV không tồn tại trong hệ thống!")
            
        email_login = response.data[0]["email"]

    # BƯỚC 2: Gọi hệ thống Supabase Auth để đăng nhập bằng Email và Password
    try:
        auth_response = supabase.auth.sign_in_with_password({
            "email": email_login, 
            "password": data.password
        })
        
        # Xử lý dữ liệu user trả về thành dạng dict để không bị lỗi 500 Pydantic với TokenResponse [1]
        user_info = {}
        if hasattr(auth_response.user, "model_dump"):
            user_info = auth_response.user.model_dump()
        elif hasattr(auth_response.user, "dict"):
            user_info = auth_response.user.dict()
        else:
            user_info = {"id": auth_response.user.id, "email": auth_response.user.email}

        return {
            "access_token": auth_response.session.access_token,
            "token_type": "bearer",
            "user": user_info
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Sai thông tin đăng nhập! Chi tiết: {str(e)}")

@app.get("/auth/me")
def get_me(token: str = Depends(get_current_token)):
    """Lấy thông tin profile từ token đã đăng nhập."""
    try:
        # 1. Lấy thông tin user hiện tại từ token của Supabase Auth [5]
        auth_user = supabase.auth.get_user(token)
        user_id = auth_user.user.id
        
        # 2. Truy vấn bảng users lấy các thông tin chi tiết (MSSV, verified,...) [2, 6]
        response = supabase.table("users").select("*").eq("id", user_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ người dùng")
            
        return response.data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ hoặc đã hết hạn",
            headers={"WWW-Authenticate": "Bearer"},
        )

def check_verified_user(token: str = Depends(get_current_token)):
    """Middleware kiểm tra xem user đã xác thực thẻ sinh viên (verified = true) chưa"""
    try:
        # 1. Lấy user_id từ token
        auth_user = supabase.auth.get_user(token)
        user_id = auth_user.user.id
        
        # 2. Truy vấn cột 'verified' từ bảng users
        response = supabase.table("users").select("verified").eq("id", user_id).execute()
        
        if len(response.data) == 0:
            raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ!")
            
        is_verified = response.data[0].get("verified", False)
        
        if not is_verified:
            raise HTTPException(status_code=403, detail="Chưa xác thực!")
            
        return user_id
        
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token không hợp lệ hoặc lỗi xác thực: {str(e)}")
from tutor_routes import router as tutor_router
app.include_router(tutor_router)
