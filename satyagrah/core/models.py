from pydantic import BaseModel, Field
from typing import Literal, List, Optional, Dict

TaskType = Literal["txt2img"]

class Task(BaseModel):
    type: TaskType
    prompt: str
    seed: int = 77
    steps: int = 28
    width: int = 768
    height: int = 1024
    count: int = 1

class Job(BaseModel):
    version: int = 1
    job_id: str
    requester: str
    ttl_hours: int = 24
    meta: Dict[str, str] = {}
    tasks: List[Task]

class ResultItem(BaseModel):
    name: str
    size: int
    mime: str

class ResultManifest(BaseModel):
    job_id: str
    items: List[ResultItem]
