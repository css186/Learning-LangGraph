import uuid
import logging
from typing import Optional
from pydantic import ValidationError

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from .redis_controller import RedisController
from .schemas import (
    StartMessage,
    QuestionMessage,
    SubmissionMessage,
    EndMessage,
    AgentState
)
from .graph import interview_agent


logger = logging.getLogger(__name__)
router = APIRouter()
redis_controller = RedisController()


@router.websocket("/ws/agent")
async def agent_ws(websocket: WebSocket):
    """
    WebSocket endpoint for the agent to handle real-time interactions.
    """
    await websocket.accept()

    thread_id: Optional[str] = None
    state: Optional[AgentState] = None

    try:
        while True:
            
            # Handling messages
            raw = await websocket.receive_json()
            title = raw.get("title", "")

            # --- Heartbeat check ---
            if title == "ping":
                await websocket.send_json({"title": "pong"})
                continue
            
            # --- Global variables check ---
            if not state or not thread_id:
                await websocket.send_json({"error": "Must start interview first"})
                continue

            # --- Start Interview ---
            if title == "start interview":
                try:
                    message = StartMessage.parse_obj(raw)
                except ValidationError:
                    await websocket.send_json({"error": "Invalid start message"})
                    continue
                
                thread_id = str(uuid.uuid4())

                # initial AgentState
                init = {
                    "thread_id": thread_id,
                    "description": message.get("description", ""),
                    "language": message.get("language", ""),
                }
                state = AgentState(**init)

                # Run graph agent
                state = await interview_agent(
                    state,
                    config={"configurable": {"thread_id": thread_id}}
                )

                await websocket.send_json({
                    "title": "start interview response",
                    "text": state.history[-1] if state.history else "",
                    "thread_id": thread_id
                })

                continue

            # --- Question Update --- 
            if title == "question":
                try:
                    message = QuestionMessage.parse_obj(raw)
                except ValidationError:
                    await websocket.send_json({"error": "Invalid question message"})
                    continue

                if message.id != thread_id:
                    await websocket.send_json({"error": "ID mismatch"})
                    continue


                state.user_input   = message.speech
                state.current_code = message.code

                # run the graph (load + merge + run + save)
                state = await interview_agent(
                    state,
                    config={"configurable": {"thread_id": thread_id}}
                )

                await websocket.send_json({
                    "title": "question response",
                    "text": state.history[-1] if state.history else ""
                })
                continue

            # --- Submission Result ---
            if title == "submission result":
                try:
                    message = QuestionMessage.parse_obj(raw)
                except ValidationError:
                    await websocket.send_json({"error": "Invalid question message"})
                    continue

                if message.id != thread_id:
                    await websocket.send_json({"error": "ID mismatch"})
                    continue

                state.status = message.status

                                # run the graph (load + merge + run + save)
                state = await interview_agent(
                    state,
                    config={"configurable": {"thread_id": thread_id}}
                )

                await websocket.send_json({
                    "title": "question response",
                    "text": state.history[-1] if state.history else ""
                })
                continue
            
                        # --- Stop Interview ---
            if title == "stop interview":
                try:
                    message = StopMessage.parse_obj(raw)
                except ValidationError:
                    await websocket.send_json({"error": "Invalid stop message"})
                    continue

                if message.id != thread_id:
                    await websocket.send_json({"error": "ID mismatch"})
                    continue

                state = await interview_agent(
                    state,
                    config={"configurable": {"thread_id": thread_id}}
                )

                await websocket.send_json({
                    "title": "evaluation response",
                    "text": state.history[-1] if state.history else ""
                })
                continue


    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {thread_id}")
    except Exception:
        logger.exception("Unexpected error")
        await websocket.close(code=1011)            


    #             # Create initial agent state
    #             initial_state = AgentState(
    #                 thread_id=thread_id,
    #                 title=message.title,
    #                 description=message.description,
    #                 language=message.language,
    #                 current_stage=title,
    #                 history=[]
    #             )

    #             await redis_controller.save_agent_state(initial_state, thread_id)


    #             try:
    #                 new_state = interview_agent(initial_state)
    #             except Exception as e:
    #                 logger.error(f"Error running interview_agent on start: {e}")
    #                 new_state = initial_state

    #             await redis_controller.save_agent_state(thread_id, new_state)

    #             first_question = ""
    #             if new_state.history:
    #                 first_question = new_state.history[-1]
    #             await websocket.send_json({
    #                 "title": "start interview response",
    #                 "text": first_question,
    #                 "thread_id": thread_id
    #             })
    #             continue

 
    #         if active_thread_id is None:
    #             await websocket.send_json({
    #                 "error": "You must send {\"title\":\"start interview\"} first."
    #             })
    #             continue

    #         incoming_thread = data.get("thread_id")
    #         if not incoming_thread or incoming_thread != active_thread_id:
    #             await websocket.send_json({
    #                 "error": "Missing or mismatched \"thread_id\"."
    #             })
    #             continue
            
    #         # DISCUSSION  
    #         if title == "question":
    #             try:
    #                 message = QuestionMessage.model_validate(data)
    #             except ValidationError:
    #                 logger.warning("Invalid JSON for 'question': %s", data)
    #                 await websocket.send_json(Utils.generate_error_response())
    #                 continue

    #             lock = await redis_controller.redis.lock(
    #                 redis_controller._lock_name(active_thread_id), timeout=10.0
    #             )
    #             async with lock:
    #                 state = await redis_controller.get_agent_state(active_thread_id)
    #                 if state is None:
    #                     state = AgentState(thread_id=active_thread_id)

    #                 state.history.append(message.speech)
    #                 state.current_code = message.code or state.current_code

    #                 try:
    #                     new_state = interview_agent(state)
    #                 except Exception as e:
    #                     logger.error(f"Error running interview_agent on question: {e}")
    #                     new_state = state

    #                 await redis_controller.save_agent_state(active_thread_id, new_state)

    #             next_question = ""
    #             if new_state.history:
    #                 next_question = new_state.history[-1]
    #             await websocket.send_json({
    #                 "title": "question response",
    #                 "text": next_question
    #             })
    #             continue

    #         #SUBMISSION RESULT
    #         if title == "submission result":
    #             try:
    #                 message = SubmissionMessage.model_validate(data)
    #             except ValidationError:
    #                 logger.warning("Invalid JSON for 'submission result': %s", data)
    #                 await websocket.send_json(Utils.generate_error_response())
    #                 continue

    #             lock = await redis_controller.redis.lock(
    #                 redis_controller._lock_name(active_thread_id), timeout=10.0
    #             )
    #             async with lock:
    #                 state = await redis_controller.get_agent_state(active_thread_id)
    #                 if state is None:
    #                     state = AgentState(thread_id=active_thread_id)

    #                 state.metrics["last_submission_result"] = json.dumps(message.result)

    #                 try:
    #                     new_state = interview_agent(state)
    #                 except Exception as e:
    #                     logger.error(f"Error running interview_agent on submission: {e}")
    #                     new_state = state

    #                 await redis_controller.save_agent_state(active_thread_id, new_state)

    #             next_prompt = ""
    #             if new_state.history:
    #                 next_prompt = new_state.history[-1]
    #             await websocket.send_json({
    #                 "title": "submission response",
    #                 "text": next_prompt
    #             })
    #             continue

    #         # END INTERVIEW
    #         if title == "end interview":
    #             try:
    #                 message = EndMessage.model_validate(data)
    #             except ValidationError:
    #                 logger.warning("Invalid JSON for 'end interview': %s", data)
    #                 await websocket.send_json(Utils.generate_error_response())
    #                 continue

    #             lock = await redis_controller.redis.lock(
    #                 redis_controller._lock_name(active_thread_id), timeout=10.0
    #             )
    #             async with lock:
    #                 # 1) Load existing state
    #                 state = await redis_controller.get_agent_state(active_thread_id)
    #                 if state is None:
    #                     state = AgentState(thread_id=active_thread_id)

    #                 # 2) Optionally mark the interview as finished
    #                 state.status = "ended"

    #                 # 3) Run LangGraph agent one final time (e.g. to summarize)
    #                 try:
    #                     new_state = interview_agent(state)
    #                 except Exception as e:
    #                     logger.error(f"Error running interview_agent on end: {e}")
    #                     new_state = state

    #                 # 4) Persist updated state (or delete if you prefer)
    #                 await redis_controller.save_agent_state(active_thread_id, new_state)

    #             # 5) Send back the final evaluation (last item in history)
    #             final_evaluation = ""
    #             if new_state.history:
    #                 final_evaluation = new_state.history[-1]
    #             await websocket.send_json({
    #                 "title": "evaluation response",
    #                 "text": final_evaluation
    #             })
    #             continue


    #         await websocket.send_json(Utils.generate_error_response())
    #         logger.warning("Invalid JSON data: unrecognized title: %s", data)

    # except WebSocketDisconnect:
    #     # Client disconnected: clean up
    #     user_id = active_thread_id or websocket.client.host
    #     await manager.disconnect(user_id)
    #     try:
    #         await websocket.close()
    #         logger.info(f"WebSocket closed for thread_id: {active_thread_id}")
    #     except Exception:
    #         logger.warning(f"Error closing WebSocket for thread_id: {active_thread_id}")
    #     finally:
    #         if active_thread_id:
    #             await redis_controller.delete(active_thread_id)
    #             logger.info(f"Deleted Redis state for thread_id: {active_thread_id}")
    #         await redis_controller.close_redis()
    #         # If your LangGraph agent holds in‐memory caches per thread, clear them:
    #         try:
    #             agent = InterviewAgent()
    #             await agent.remove_thread(active_thread_id)
    #             logger.info(f"Cleared agent resources for thread_id: {active_thread_id}")
    #         except Exception:
    #             pass

    # except Exception as e:
    #     logger.error(f"Unexpected error in WebSocket handler: {e}")
    #     await websocket.close(code=1011)
    #     if active_thread_id:
    #         await redis_controller.delete(active_thread_id)
    #         await redis_controller.close_redis()
    #         try:
    #             agent = InterviewAgent()
    #             await agent.remove_thread(active_thread_id)
    #         except Exception:
    #             pass


                


    