from typing import Annotated
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
import os
from model.user import User
from typing import Any

security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
):
    try:
        token = credentials.credentials
        decoded_token = jwt.decode(token, "ebay-project", algorithms=["HS256"])
        user_id = decoded_token["id"]
        user = await User.get(id=user_id)
        return user
    except:
        raise HTTPException(
            401,
            "Unauthorized"
        )

CurrentUser = Annotated[User, Depends(get_current_user)]