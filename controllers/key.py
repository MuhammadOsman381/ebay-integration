from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from tortoise.exceptions import DoesNotExist
from model.key import Key
import os
from typing import Optional
from helpers.get_current_user import CurrentUser

router = APIRouter(prefix="/api/key", tags=["Key"])


class CreateKeys(BaseModel):
    token: Optional[str] = None
    apiKey: Optional[str] = None


@router.post("/create")
async def create_key(data: CreateKeys, user: CurrentUser): 
    key = await Key.get_or_none()
    if not key:
        if data.token:
            await Key.create(token=data.token)
        else:
            await Key.create(api_key=data.apiKey)
    else:
        if data.token:
            key.token = data.token
            key.api_key = None
            await key.save()
        else:
            key.token = None
            key.api_key = data.apiKey
            await key.save()

    return {"message": "Keys processed successfully"}
