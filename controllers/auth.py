from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from tortoise.exceptions import DoesNotExist
from argon2 import PasswordHasher
from model.user import User
from helpers.token import create_access_token
import os 

router = APIRouter(
    prefix="/api/auth",
    tags=["Auth"]
)

ph = PasswordHasher()

class Login(BaseModel):
    email: str
    password: str

@router.get("/create-admin")
async def create_admin():
    email = "admin@gmail.com"
    password = "123456"
    existing = await User.filter(email=email).first()
    if existing:
        return {"message": "Admin already exists"}
    hashed = ph.hash(password)
    await User.create(email=email, password=hashed, is_admin=True)
    return {"message": "Admin created successfully"}


@router.post("/login")
async def login(data: Login):
    try:
        user = await User.get(email=data.email)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        ph.verify(user.password, data.password)  
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid password")
    token = create_access_token({"id": user.id})
    return {
        "message": "Login successful",
        "token": token
    }
