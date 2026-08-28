from pydantic import BaseModel, Field, field_validator, ValidationError

class CustomerResponse(BaseModel):
    tone: str = Field(description="The detected tone of the message.")
    message: str = Field(description="The actual message to send to the user.")
    
    @field_validator('message')
    @classmethod
    def prevent_competitor_mentions(cls, v: str) -> str:
        # A semantic guardrail to prevent the agent from mentioning competitors
        banned_words = ['competitor_a', 'competitor_b']
        if any(word in v.lower() for word in banned_words):
            raise ValueError("Guardrail triggered: Message contains a mention of a competitor.")
        return v
        
    @field_validator('tone')
    @classmethod
    def force_polite_tone(cls, v: str) -> str:
        # A strict enum-style guardrail
        if v.lower() not in ['polite', 'professional', 'empathetic']:
            raise ValueError(f"Guardrail triggered: Unacceptable tone '{v}'. Must be polite, professional, or empathetic.")
        return v
