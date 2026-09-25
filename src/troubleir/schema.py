from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, field_validator
import re


class BaseDeeplink(BaseModel):
    deeplink: str


class Deeplink(BaseDeeplink):
    description: str
    message: Optional[str] = ""
    classes: Optional[Dict[str, str]] = None
    originalType: Optional[str] = None


class Condition(str, Enum):
    greater = "greater"
    equal = "equal"
    less = "less"


class ResultTypes(str, Enum):
    boolean = "boolean"
    intNum = "integer"
    string = "str"
    floatNum = "float"


class actionCategory(str, Enum):
    auto = "auto"
    manual = "manual"
    critical = "critical"


class ValidationDeeplink(BaseDeeplink):
    key: str
    resultType: Optional[ResultTypes] = None
    condition: Optional[Condition] = None
    value: Optional[str] = None


class StepGroup(BaseModel):
    steps: List[str]
    validationDeeplink: Optional[ValidationDeeplink] = None
    actionableDeeplink: Optional[Deeplink] = None


class Action(BaseModel):
    actionName: str
    description: str
    stepGroups: List[StepGroup]
    category: Optional[actionCategory] = actionCategory.manual

    @field_validator("description")
    @classmethod
    def description_starts_with_it_will(cls, v: str) -> str:
        if not v.startswith("It will"):
            raise ValueError("description must start with 'It will'")
        return v


class Goal(BaseModel):
    goal: str
    title: str
    actions: List[Action]
    score: float

    @field_validator("score")
    @classmethod
    def score_in_range(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("score must be between 0.0 and 1.0")
        return v


class ContextDeeplinkResponse(BaseModel):
    """RAG response containing a list of Goal objects."""
    contexts: List[Goal] = []
    fallback: Optional[str] = None


# Extended response with meta (for API layer)
class TroubleshootResponse(BaseModel):
    query: str
    query_variations: List[str] = []
    response: ContextDeeplinkResponse
    meta: Dict = {}


# Internal diagnostics
class DiagnosticCode(str, Enum):
    UNGROUNDED_OPERATION = "E204"
    PARENT_MENU_MATCH = "E310"
    INVALID_DEEPLINK = "E401"
    URL_LEAK = "E402"
    SCHEMA_FAILURE = "E403"
    CACHE_POLARITY_MISMATCH = "E501"
    CACHE_SLOT_MISMATCH = "E502"
    STALE_DEPENDENCY = "E601"
    LOW_RELIABILITY = "E701"


URL_PATTERN = re.compile(
    r"https?://\S+|www\.\S+",
    re.IGNORECASE,
)
# Patterns that indicate hallucinated web URLs (not bixby deeplinks)
_WEB_PATTERN = re.compile(
    r"https?://(?!dummy|masked)|www\.\w+\.(com|org|net|io|samsung)",
    re.IGNORECASE,
)


def has_url_leak(text: str) -> bool:
    """Return True if text contains a web URL leak (not bixby:// deeplinks)."""
    # Remove bixby:// deeplinks before checking
    cleaned = re.sub(r"bixby://\S+", "", text)
    return bool(URL_PATTERN.search(cleaned))
