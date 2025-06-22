from typing import Any, Dict, List, Optional, Union
from langchain_core.messages import BaseMessage
from langchain_core.runnables import Runnable
from langgraph.graph import StateGraph, START, END
from langchain import hub
from langchain.agents import AgentExecutor, create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os
load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-exp",
    google_api_key=gemini_api_key,
    temperature=0.7,
    max_output_tokens=1024
)