from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.document import Document, DocumentStatus


class DocumentRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self._collection = db.documents

    async def create(self, document: Document) -> Document:
        result = await self._collection.insert_one(document.to_mongo())
        document.id = result.inserted_id
        return document

    async def get_by_id(self, document_id: ObjectId) -> Document | None:
        raw = await self._collection.find_one({"_id": document_id})
        return Document(**raw) if raw else None

    async def list_all(self) -> list[Document]:
        cursor = self._collection.find().sort("created_at", -1)
        return [Document(**raw) async for raw in cursor]

    async def update_status(
        self, document_id: ObjectId, status: DocumentStatus, error_message: str | None = None
    ) -> None:
        await self._collection.update_one(
            {"_id": document_id},
            {
                "$set": {
                    "status": status,
                    "error_message": error_message,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )

    async def update_processing_result(
        self, document_id: ObjectId, *, page_count: int, chunk_count: int
    ) -> None:
        await self._collection.update_one(
            {"_id": document_id},
            {
                "$set": {
                    "page_count": page_count,
                    "chunk_count": chunk_count,
                    "status": DocumentStatus.READY,
                    "error_message": None,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )

    async def delete(self, document_id: ObjectId) -> bool:
        result = await self._collection.delete_one({"_id": document_id})
        return result.deleted_count > 0

    async def count(self) -> int:
        return await self._collection.count_documents({})

    async def exist(self, document_ids: list[ObjectId]) -> bool:
        if not document_ids:
            return True
        found = await self._collection.count_documents({"_id": {"$in": document_ids}})
        return found == len(set(document_ids))
