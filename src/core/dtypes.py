from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Transaction:
    date: datetime
    amount: float
    description: str
    currency: str = "RUB"
    category: Optional[str] = None
    comment: Optional[str] = None

@dataclass
class UserNote:
    id: int
    text: str
    timestamp: datetime