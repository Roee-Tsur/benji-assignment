import uuid
from typing import Literal

IdPrefix = Literal["ep", "evt", "dlv", "att", "lease"]


def new_id(prefix: IdPrefix) -> str:
    """Prefixed IDs (`ep_…`, `evt_…`, `dlv_…`) say what they identify wherever they show up."""
    return f"{prefix}_{uuid.uuid4().hex}"
