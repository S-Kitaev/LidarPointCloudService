from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    user_name: str
    password: str
    email: EmailStr | None = None

class UserRead(BaseModel):
    id: int
    user_name: str
    email: EmailStr | None

    class Config:
        from_attributes = True