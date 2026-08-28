from pydantic import BaseModel, Field, field_validator

class RefundInput(BaseModel):
    user_id: int = Field(description="The unique numerical ID of the user.")
    amount: float = Field(description="The refund amount. Must be positive.")
    reason: str = Field(description="A short explanation of why the refund is being issued.")

    @field_validator('amount')
    @classmethod
    def amount_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Refund amount must be strictly positive.')
        return v

class UserLookupInput(BaseModel):
    email: str = Field(description="The user's email address.")

class ResetPasswordInput(BaseModel):
    user_id: int = Field(description="The user ID to reset.")
