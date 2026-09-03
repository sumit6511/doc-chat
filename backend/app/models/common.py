"""Shared helpers for Mongo-backed domain models."""

from __future__ import annotations

from typing import Annotated, Any

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field, GetCoreSchemaHandler
from pydantic_core import core_schema


class _ObjectIdPydanticAnnotation:
    """Lets pydantic v2 validate/serialize bson.ObjectId as a plain string."""

    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: Any, _handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        def validate(value: Any) -> ObjectId:
            if isinstance(value, ObjectId):
                return value
            if isinstance(value, str) and ObjectId.is_valid(value):
                return ObjectId(value)
            raise ValueError(f"Invalid ObjectId: {value!r}")

        return core_schema.json_or_python_schema(
            json_schema=core_schema.no_info_plain_validator_function(validate),
            python_schema=core_schema.no_info_plain_validator_function(validate),
            # when_used="json" is essential: these models are dumped in python
            # mode via to_mongo() to build the dict handed to PyMongo/Motor,
            # which must keep real bson.ObjectId values (not strings) so
            # equality queries like {"document_id": some_object_id} match what
            # was actually stored. Only JSON-mode dumps stringify.
            serialization=core_schema.plain_serializer_function_ser_schema(str, when_used="json"),
        )


PyObjectId = Annotated[ObjectId, _ObjectIdPydanticAnnotation]


class MongoBaseModel(BaseModel):
    """Base for documents stored in MongoDB: adds a string-serialized `_id`."""

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    # alias="_id" is what actually lets Model(**raw_mongo_doc) populate `id`
    # from a real find()/aggregate() result — without it, pydantic has no
    # idea `_id` and `id` are the same field, silently drops the unknown
    # `_id` key (default `extra="ignore"`), and every record read back from
    # Mongo ends up with id=None. populate_by_name=True then lets `id=...`
    # keep working too (e.g. plain construction in tests/services).
    id: PyObjectId | None = Field(default=None, alias="_id")

    def to_mongo(self) -> dict[str, Any]:
        """Dict ready for insertion, dropping `id` when unset (let Mongo generate it)."""
        data = self.model_dump(by_alias=False, exclude={"id"})
        if self.id is not None:
            data["_id"] = self.id
        return data
