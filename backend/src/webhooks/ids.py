import uuid


def new_id(prefix: str) -> str:
    """Prefixed IDs (`ep_…`, `evt_…`, `dlv_…`) say what they identify wherever they show up."""
    return f"{prefix}_{uuid.uuid4().hex}"
