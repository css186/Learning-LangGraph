import redis.asyncio as redis
import logging
import json
from pydantic import ValidationError
from typing import Optional, List

from .config import settings
from .schemas import AgentState

logger = logging.getLogger(__name__)

class RedisController:
    def __init__(self):
        self.redis = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True
        )
        self._ttl_seconds = 60 * 50  # 50 minutes
        logger.info(f"RedisController initialized with host={settings.REDIS_HOST}, port={settings.REDIS_PORT}, db={settings.REDIS_DB}")

    def __cache_key_prefix(self, thread_id: str) -> str:
        """
        Generate a cache key prefix based on the thread_id.
        """
        return f"agent_state:{thread_id}"

    def __serialize_state(self, state: AgentState) -> str:
        """
        Serialize the AgentState to a JSON string.
        """
        return state.json()

    def __deserialize_state(self, raw_json: str) -> AgentState:
        """
        Deserialize a JSON string to an AgentState object.
        """
        return AgentState.parse_raw(raw_json)

    def __lock_name(self, thread_id: str) -> str:
        """
        Generate a lock name based on the thread_id.
        """
        return f"lock:agent_state:{thread_id}"

    async def get_agent_state(self, thread_id: str) -> Optional[AgentState]:
        """
        Retrieve the agent state from Redis by thread_id.
        """
        try:
            # Construct the key
            key = self.__cache_key_prefix(thread_id)
            # Get raw JSON
            raw_json = await self.redis.get(key)
            if not raw_json:
                return None
            
            state = self.__deserialize_state(raw_json)
            logger.info(f"[Redis] Retrieved agent state for thread_id {thread_id}: {state}")
            return state
        
        except Exception as e:
            logger.error(f"[Redis] Error retrieving agent state for thread_id {thread_id}: {e}")
            return None

    async def save_agent_state(self, thread_id: str, state: AgentState) -> bool:
        """
        Save the agent state to Redis by thread_id.
        """
        try:
            # Construct the key
            key = self.__cache_key_prefix(thread_id)
            # Serialize state to JSON
            state_json_str = self.__serialize_state(state)
            await self.redis.set(key, state_json_str, ex=self._ttl_seconds) # 50 minutes TTL
            logger.info(f"[Redis] Saved agent state for thread_id {thread_id}: {state}")
            return True
        except Exception as e:
            logger.error(f"[Redis] Error saving agent state for thread_id {thread_id}: {e}")
            return False

    async def update_agent_state(self, thread_id: str, payload: dict) -> bool:
        """
        1. Update the agent state with the payload provided, and store it back
        2. Wrapped in a Redis lock
        """
        key = self.__cache_key_prefix(thread_id)
        lock_name = self.__lock_name(thread_id)

        # Create a lock, timeout after 5 seconds to avoid deadlocks
        lock = await self.redis.lock(lock_name, timeout=5.0)
        
        async with lock:
            # Load
            try:
                raw_json = await self.redis.get(key)
                if raw_json:
                    state = self.__deserialize_state(raw_json)
                else:
                    state = AgentState()

            except Exception as e:
                logger.error(f"[Redis] Error loading agent state for thread_id {thread_id}: {e}")
                return False

            # Merge
            try:
                state_dict = state.dict()
                state_dict.update(payload)
                updated_state = AgentState(**state_dict)
            
            except ValidationError as ve:
                logger.error(f"[Redis] Validation error while updating agent state for thread_id {thread_id}: {ve}")
                return False

            except Exception as e:
                logger.error(f"[Redis] Error merging payload into agent state for thread_id {thread_id}: {e}")
                return False

            # Save
            try:
                state_json_str = self.__serialize_state(updated_state)
                await self.redis.set(key, state_json_str, ex=self._ttl_seconds)  # Set TTL
                logger.info(f"[Redis] Updated agent state for thread_id {thread_id}: {updated_state}")
                return True
            except Exception as e:
                logger.error(f"[Redis] Error saving updated agent state for thread_id {thread_id}: {e}")
                return False

    async def get_all_records(self) -> List[AgentState]:
        """
        Retrieve all agent states from Redis.
        """
        try:
            keys = await self.redis.keys("agent_state:*")
            records = []
            for key in keys:
                raw_json = await self.redis.get(key)
                if raw_json:
                    state = self.__deserialize_state(raw_json)
                    records.append(state)
            logger.info(f"Retrieved {len(records)} records from Redis.")
            return records
        except Exception as e:
            logger.error(f"Error retrieving all records: {e}")
            return []


    