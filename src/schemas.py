from pydantic import BaseModel
from datetime import timedelta
from typing import List
from typing import Optional
from fastapi import Request

class Pengguna(BaseModel):
    username: str
    password: str

class JWTSettings(BaseModel):
    authjwt_secret_key: str = "6969696969"
    access_expires: int = timedelta(minutes=30)
    refresh_expires: int = timedelta(days=30)

class CsrfSettings(BaseModel):
    secret_key: str = 'ohasmara!'
    cookie_samesite: str = 'lax'
    

class UserCreateForm:
    def __init__(self, request: Request):
        self.request: Request = request
        self.errors: List = []
        self.username: Optional[str] = None
        self.password: Optional[str] = None

    async def load_data(self):
        form = await self.request.form()
        self.username = form.get("username")
        self.password = form.get("password")

    async def is_valid(self):
        if not self.username or not len(self.username) > 3:
            self.errors.append("Username should be > 3 chars")
        if not self.password or not len(self.password) >= 4:
            self.errors.append("Password must be > 4 chars")
        if not self.errors:
            return True
        return False