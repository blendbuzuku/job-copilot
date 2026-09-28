"""Shapes of the JSON the API sends and receives (validated by Pydantic)."""
from pydantic import BaseModel, ConfigDict


class ProfileIn(BaseModel):
    name: str = ""
    cv_text: str


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    cv_text: str
    chunk_count: int = 0
