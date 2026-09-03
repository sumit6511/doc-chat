from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.conversation import Conversation


class ConversationRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self._collection = db.conversations

    async def create(self, conversation: Conversation) -> Conversation:
        result = await self._collection.insert_one(conversation.to_mongo())
        conversation.id = result.inserted_id
        return conversation

    async def get_by_id(self, conversation_id: ObjectId) -> Conversation | None:
        raw = await self._collection.find_one({"_id": conversation_id})
        return Conversation(**raw) if raw else None

    async def list_all(self) -> list[Conversation]:
        cursor = self._collection.find().sort("updated_at", -1)
        return [Conversation(**raw) async for raw in cursor]

    async def update(self, conversation_id: ObjectId, updates: dict) -> None:
        updates = {**updates, "updated_at": datetime.now(timezone.utc)}
        await self._collection.update_one({"_id": conversation_id}, {"$set": updates})

    async def touch(self, conversation_id: ObjectId) -> None:
        await self._collection.update_one(
            {"_id": conversation_id}, {"$set": {"updated_at": datetime.now(timezone.utc)}}
        )

    async def delete(self, conversation_id: ObjectId) -> bool:
        result = await self._collection.delete_one({"_id": conversation_id})
        return result.deleted_count > 0
