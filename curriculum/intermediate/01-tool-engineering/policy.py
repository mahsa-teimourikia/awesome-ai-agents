from pydantic import BaseModel, Field

class RefundInput(BaseModel):
    user_id: int = Field(description="The unique numerical ID of the user.")
    amount: float = Field(description="The refund amount. Must be positive.")
    reason: str = Field(description="A short explanation of why the refund is being issued.")

class UserLookupInput(BaseModel):
    email: str = Field(description="The user's email address.")

class ResetPasswordInput(BaseModel):
    user_id: int = Field(description="The user ID to reset.")
