from pydantic import BaseModel


class WorkItem(BaseModel):
    id: str
    title: str
    description: str
    created_at: str
    updated_at: str
    url: str
