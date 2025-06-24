from typing import Any, Dict, List, Optional, Union
from langchain_core.messages import BaseMessage
from langchain_core.runnables import Runnable
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langchain import hub
from langchain.agents import AgentExecutor, create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os
from backend.app.routers.cart import *
from sqlalchemy.orm import Session
from fastapi import Depends
from .. import schemas, database, oauth2
from fastapi import Depends
from sqlalchemy.orm import Session
from backend.app import schemas, database, oauth2
load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=gemini_api_key,
    temperature=0.7,
    max_output_tokens=1024
)

@tool
def agent_cart_adder(cart_item: schemas.CartCreate,current_user):
    '''
    Agent uses this tool to add an item to the cart.
    
    '''
    db_gen = database.get_db()
    db = next(db_gen)
    try:
        return add_to_cart(cart_item=cart_item, db=db, current_user=current_user)
    finally:
        db_gen.close() 
@tool 
def agent_delete_cart_item(product_id: int, current_user):
    
    db_gen = database.get_db()
    db = next(db_gen)
    try:
        return remove_product_from_cart(product_id=product_id, db=db, current_user=current_user)
    finally:
        db_gen.close()
@tool 
def agent_update_cart_item(product_id: int, cart_item: schemas.CartCreate, current_user):
    
    db_gen = database.get_db()
    db = next(db_gen)
    try:
        return update_cart_item(product_id=product_id, cart_item=cart_item, db=db, current_user=current_user)
    finally:
        db_gen.close()
@tool
def agent_get_cart(current_user):
    db_gen = database.get_db()
    db = next(db_gen)
    try:
        return get_cart(db=db, current_user=current_user)
    finally:
        db_gen.close()
@tool 
def agent_order(address: str, total_amount: float, current_user):
    db_gen = database.get_db()
    db = next(db_gen)
    try:
        return checkout()
    finally:
        db_gen.close()



 


class AgentMain(StateGraph):
    def __init__(self, system_prompt: Optional[str] = None):
        self.llm=llm
        self.system_prompt = system_prompt or "You are a helpful shopping assistant."
        
        
    