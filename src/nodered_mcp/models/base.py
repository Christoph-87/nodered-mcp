"""Base API model with generic from_api() class method."""

from typing import Any, Self, overload

from pydantic import BaseModel, ConfigDict


class BaseApiModel(BaseModel):
    """Base model for all API response objects.

    Provides a generic from_api() that delegates to model_validate().
    Provider-specific subclasses override field mapping via
    @field_validator(mode='before') and @model_validator(mode='before').
    """

    model_config = ConfigDict(populate_by_name=True)

    @overload
    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Self: ...

    @overload
    @classmethod
    def from_api(cls, data: list[dict[str, Any]]) -> list[Self]: ...

    @classmethod
    def from_api(cls, data: dict[str, Any] | list[dict[str, Any]]) -> "Self | list[Self]":
        """Create model instance(s) from API response data.

        Args:
            data: Single dict or list of dicts from provider API.

        Returns:
            Single model or list of models.
        """
        if isinstance(data, list):
            return [cls.model_validate(item) for item in data]
        return cls.model_validate(data)
