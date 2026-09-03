from __future__ import annotations

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.message import Message


class MessageRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self._collection = db.messages

    async def create(self, message: Message) -> Message:
        result = await self._collection.insert_one(message.to_mongo())
        message.id = result.inserted_id
        return message

    async def list_by_conversation(self, conversation_id: ObjectId) -> list[Message]:
        cursor = self._collection.find({"conversation_id": conversation_id}).sort("created_at", 1)
        return [Message(**raw) async for raw in cursor]

    async def list_recent(self, conversation_id: ObjectId, limit: int) -> list[Message]:
        """Most recent `limit` messages, returned in chronological order."""
        cursor = (
            self._collection.find({"conversation_id": conversation_id})
            .sort("created_at", -1)
            .limit(limit)
        )
        recent = [Message(**raw) async for raw in cursor]
        return list(reversed(recent))

    async def count_by_conversation(self, conversation_id: ObjectId) -> int:
        return await self._collection.count_documents({"conversation_id": conversation_id})

    async def delete_by_conversation(self, conversation_id: ObjectId) -> int:
        result = await self._collection.delete_many({"conversation_id": conversation_id})
        return result.deleted_count
