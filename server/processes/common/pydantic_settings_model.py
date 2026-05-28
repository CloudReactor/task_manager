from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


DEFAULT_STR_MAX_LENGTH = 5000

EXCLUDE_IF_NONE = lambda v: v is None


class PydanticSettingsModel(BaseModel):
    model_config = ConfigDict(
        str_max_length=DEFAULT_STR_MAX_LENGTH,
        str_strip_whitespace=True,
        extra='forbid',
    )

    def model_dump(self, **kwargs) -> dict[str, Any]:
        kwargs.setdefault('mode', 'json')
        kwargs.setdefault('exclude_unset', True)
        return super().model_dump(**kwargs)
