from typing import TypedDict, Annotated, Dict, Any,List,Union
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.tools import tool
import uuid
import pandas as pd
import sqlite3
from dotenv import load_dotenv
from logger_setup import get_logger

logger = get_logger(__name__)


load_dotenv()

# 1. Define the Agent's State
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


# 2. --------------Define the Nodes (Functions)------------------

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.7,
)

from langchain_core.runnables.config import RunnableConfig

store = InMemoryStore()

@tool
def save_memory(memory: str):
    """"Save an important fact or preference about the user to memory."""
    namespace = ("memories", "user_1")
    store.put(namespace, str(uuid.uuid4()), {"memory": memory})
    logger.info(f"Saved memory: {memory}")
    return f"Saved memory: {memory}"

tools = [save_memory]
llm_with_tools = llm.bind_tools(tools)
tool_node = ToolNode(tools)

def chatbot(state: AgentState, config: RunnableConfig):
    """The main node that calls the LLM."""
    user_id = config.get("configurable", {}).get("user_id", "user_1")
    namespace = ("memories", user_id)
    memories = store.search(namespace)
    info = "\n".join([f"- {m.value.get('memory')}" for m in memories]) if memories else "None"
    sys_msg = SystemMessage(
        content=f"You are a helpful assistant with memory. Use the save_memory tool to save facts about the user. Here are facts you know:\n{info}"
    )
    
    # Prepend the system message to the current conversation
    messages = [sys_msg] + state["messages"]
    
    response = llm_with_tools.invoke(messages)
    
    return {"messages": [response]}


# 3. ----------------Building connections graph -----------

graph = StateGraph(AgentState)
graph.add_node("chatbot", chatbot)
graph.add_node("tools", tool_node)

graph.add_edge(START, "chatbot")
graph.add_conditional_edges("chatbot", tools_condition)
graph.add_edge("tools", "chatbot")

checkpointer = MemorySaver()
app = graph.compile(checkpointer=checkpointer, store=store)


# 4. -----------------Running the chatbot------------------

if __name__ == "__main__":
    config = {"configurable": {"thread_id": "thread_1", "user_id": "user_1"}}

    logger.info("Chatbot started! Type 'exit' to quit.")
    print("Chatbot started! Type 'exit' to quit.")
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            break

        state_update = {"messages": [HumanMessage(content=user_input)]}
        result = app.invoke(state_update, config=config)
        
        last_message = result["messages"][-1]
        if isinstance(last_message, AIMessage) and last_message.content:
            content = last_message.content
            if isinstance(content, list) and len(content) > 0 and isinstance(content[0], dict) and "text" in content[0]:
                content = content[0]["text"]
            logger.info(f"AI response provided: {content}")
            print(f"AI: {content}")

