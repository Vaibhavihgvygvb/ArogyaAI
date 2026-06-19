from app.ai.medical.engine.schemas import ConversationContext
from app.ai.memory.deps import get_memory_manager


class ContextResolver:
    async def resolve(self, conversation_id: str) -> ConversationContext:
        try:
            mgr = get_memory_manager()
            conversation = await mgr.get_conversation(conversation_id)
            if not conversation:
                return ConversationContext(
                    conversation_id=conversation_id,
                    has_context=False,
                )

            messages = conversation.messages
            previous_queries = [
                m.content for m in messages
                if m.role == "user"
            ]

            return ConversationContext(
                conversation_id=conversation_id,
                previous_queries=previous_queries,
                active_topics=list(set(
                    m.metadata.get("topic", "") for m in messages
                    if m.metadata and m.metadata.get("topic")
                )),
                message_count=len(messages),
                has_context=True,
            )
        except Exception:
            return ConversationContext(
                conversation_id=conversation_id,
                has_context=False,
            )
