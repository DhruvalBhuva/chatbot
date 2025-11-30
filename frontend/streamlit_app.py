# frontend/streamlit_app.py

import os
import sys

import queue
import uuid

import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.main import chatbot, retrieve_all_threads, submit_async_task


# =========================== Utilities ===========================
def generate_thread_id():
    return str(uuid.uuid4())


def reset_chat():
    thread_id = generate_thread_id()
    st.session_state["thread_id"] = thread_id
    add_thread(thread_id)
    st.session_state["message_history"] = []


def add_thread(thread_id):
    if thread_id not in st.session_state["chat_threads"]:
        # New threads should appear at the top
        st.session_state["chat_threads"].insert(0, thread_id)


def load_conversation(thread_id):
    """Loads the message history for a given thread_id."""
    # The checkpointer needs the thread_id to retrieve the state
    config = {"configurable": {"thread_id": thread_id}}
    try:
        state = chatbot.get_state(config=config)
        # Check if messages key exists in state values, return empty list if not
        return state.values.get("messages", [])
    except Exception:
        # Handle case where thread_id might not exist in DB yet (e.g., initial load)
        return []


# ======================= Session Initialization ===================
if "message_history" not in st.session_state:
    st.session_state["message_history"] = []

if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = generate_thread_id()

if "chat_threads" not in st.session_state:
    # Initialize chat threads from the checkpointer
    st.session_state["chat_threads"] = retrieve_all_threads()

add_thread(st.session_state["thread_id"])

# ============================ Sidebar ============================
st.sidebar.title("🤖 LangGraph MCP Chatbot")

if st.sidebar.button("➕ New Chat"):
    reset_chat()

st.sidebar.header("My Conversations")
# Displaying threads in the order they were initialized/added (most recent first)
for thread_id in st.session_state["chat_threads"]:
    # Use a more readable label for the button
    label = f"💬 Chat - {thread_id[:8]}"
    if st.sidebar.button(label, key=f"sidebar_btn_{thread_id}"):
        st.session_state["thread_id"] = thread_id

        # Load messages for the selected thread
        messages = load_conversation(thread_id)

        # Convert BaseMessage objects to Streamlit-friendly dictionary format
        temp_messages = []
        for msg in messages:
            role = "user" if isinstance(msg, HumanMessage) else "assistant"
            # Extract content from BaseMessage
            content = msg.content if hasattr(msg, "content") else str(msg)
            temp_messages.append({"role": role, "content": content})

        st.session_state["message_history"] = temp_messages


# ============================ Main UI ============================

st.markdown(f"**Current Thread ID:** `{st.session_state['thread_id'][:8]}`")

# Render history
for message in st.session_state["message_history"]:
    with st.chat_message(message["role"]):
        # Streamlit's st.markdown handles most content better than st.text
        st.markdown(message["content"])

user_input = st.chat_input("Type here")

if user_input:
    # Show user's message immediately
    st.session_state["message_history"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    CONFIG = {
        "configurable": {"thread_id": st.session_state["thread_id"]},
        "metadata": {"thread_id": st.session_state["thread_id"]},
        "run_name": "chat_turn",
    }

    # Assistant streaming block
    with st.chat_message("assistant"):
        # Use a mutable holder so the generator can set/modify it
        status_holder = {"box": None}

        def ai_only_stream():
            """Generator to stream chunks from the LangGraph astream."""
            event_queue: queue.Queue = queue.Queue()

            async def run_stream():
                """Asynchronously runs the graph and puts events into the queue."""
                try:
                    async for message_chunk, metadata in chatbot.astream(
                        {"messages": [HumanMessage(content=user_input)]},
                        config=CONFIG,
                        # IMPORTANT: Stream in "messages" mode to get all messages (AI and Tool)
                        stream_mode="messages",
                    ):
                        event_queue.put((message_chunk, metadata))
                except Exception as exc:
                    event_queue.put(("error", exc))
                finally:
                    event_queue.put(None)

            # Schedule the async execution on the backend thread
            submit_async_task(run_stream())

            while True:
                item = event_queue.get()
                if item is None:
                    break
                message_chunk, metadata = item
                if message_chunk == "error":
                    raise metadata

                # Tool Message Handling (for status updates)
                if isinstance(message_chunk, ToolMessage):
                    tool_name = getattr(message_chunk, "name", "tool")
                    if status_holder["box"] is None:
                        # Lazily create the status box
                        status_holder["box"] = st.status(
                            f"🔧 Running `{tool_name}` …", expanded=True
                        )
                    else:
                        # Update the existing status box
                        status_holder["box"].update(
                            label=f"🔧 Running `{tool_name}` …",
                            state="running",
                            expanded=True,
                        )

                # Stream ONLY assistant tokens
                if isinstance(message_chunk, AIMessage):
                    yield message_chunk.content

        # Stream the LLM response to the UI
        try:
            ai_message = st.write_stream(ai_only_stream())
        except Exception as e:
            ai_message = f"An error occurred: {e}"
            st.error(ai_message)

        # Finalize only if a tool was actually used
        if status_holder["box"] is not None:
            status_holder["box"].update(
                label="✅ Tool finished", state="complete", expanded=False
            )

    # Save final assistant message to history
    st.session_state["message_history"].append(
        {"role": "assistant", "content": ai_message}
    )
