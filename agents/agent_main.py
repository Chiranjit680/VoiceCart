from typing import Any, Dict, List, Optional, Union
from langchain_core.messages import BaseMessage
from langchain_core.runnables import Runnable
from langgraph.graph import StateGraph, START, END
from langchain import hub
from langchain.agents import AgentExecutor, create_react_agent

class AgentState(StateGraph):
    