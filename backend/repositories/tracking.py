"""Read-only tracking-group repository backed by tracking.json."""

from pathlib import Path

from backend.models import TrackingGroup
from backend.models.source import TrackingFileSource
from backend.repositories.exceptions import RecordNotFoundError
from backend.repositories.loader import load_json_model


class TrackingRepository:
    """Load, cache and query local carrier mappings by tracking group ID."""

    def __init__(self, path: Path) -> None:
        source = load_json_model(path, TrackingFileSource)
        groups = tuple(
            TrackingGroup(
                tracking_group_id=group_id,
                carrier=record.carrier,
                tracking_number=record.tracking_number,
            )
            for group_id, record in source.root.items()
        )
        self._groups = groups
        self._by_group_id = {group.tracking_group_id: group for group in groups}

    def list_tracking_groups(self) -> tuple[TrackingGroup, ...]:
        return self._groups

    def get_by_group_id(self, tracking_group_id: str) -> TrackingGroup:
        try:
            return self._by_group_id[tracking_group_id]
        except KeyError:
            raise RecordNotFoundError("tracking group") from None
