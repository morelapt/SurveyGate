from pydantic import BaseModel, field_validator


class PublicResponseIn(BaseModel):
    answers: dict

    @field_validator("answers")
    @classmethod
    def validate_answers_not_empty(cls, v: dict) -> dict:
        if not v:
            raise ValueError("answers must not be empty")
        return v
