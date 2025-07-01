from typing import Any, Dict, List, Optional, Union, TypedDict
from collections import deque
from datetime import datetime
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.runnables import Runnable
from langchain_core.tools import tool
from langchain_core.prompts import PromptTemplate
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
import shopinglist_react_agent, cartmanager_agent, recipe_shopping_agent
from backend.app import schemas, database, oauth2

load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")
from .. import models
redis_url = os.getenv("redis_url", "redis://127.0.0.1:6379")

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=gemini_api_key,
    temperature=0.7,
    max_output_tokens=1024
)


class AgentState(TypedDict):
    """State for the Agent."""
    messages: List[BaseMessage]
    user_id: int
    current_agent: Optional[str]
    output: Optional[str]
    output_data: Optional[Dict[str, Any]]


class SuperAgent:
    """Super Agent that manages multiple agents using a LangGraph workflow."""

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.messages = deque(maxlen=10)
        
        # Initialize specialized agents
        self.shopping_list_agent = shopinglist_react_agent.initialize_react_agent(user_id)
        self.cart_manager_agent = cartmanager_agent.initialize_cart_manager_agent(user_id)
        self.recipe_agent = recipe_shopping_agent.initialize_recipe_agent(user_id)
        
        # Initialize cart
        self.cart: List[schemas.CartOut] = []
        
        # Initialize the agent workflow graph
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the agent workflow graph."""
        # Create the graph with the AgentState
        workflow = StateGraph(AgentState)
        
        # Add nodes for router and each specialized agent
        workflow.add_node("router", self._route_to_agent)
        workflow.add_node("shopping-list", self._run_shopping_list_agent)
        workflow.add_node("cart-manager", self._run_cart_manager_agent)
        workflow.add_node("recipe-shopping", self._run_recipe_agent)
        workflow.add_node("human_review", self._human_review)
        
        # Define the edges
        workflow.add_edge(START, "router")
        
        # Remove the direct edges and only use conditional edges from router
        workflow.add_conditional_edges(
            "router",
            lambda state: state["current_agent"],
            {
                "shopping-list": "shopping-list",
                "cart-manager": "cart-manager",
                "recipe-shopping": "recipe-shopping",
                "end": END  # Handle end of conversation
            }
        )
        
        # Add edges from agents to human review
        workflow.add_edge("shopping-list", "human_review")
        workflow.add_edge("cart-manager", "human_review")
        workflow.add_edge("recipe-shopping", "human_review")
        
        # Change this line - don't loop back to router, use conditional edge instead
        # workflow.add_edge("human_review", "router")
        
        # Add conditional edge from human_review to either END or router based on should_end flag
        workflow.add_conditional_edges(
            "human_review",
            lambda state: state.get("should_end", False),
            {
                True: END,
                False: "router"
            }
        )
        
        return workflow.compile()
    def _human_review(self, state: AgentState) -> AgentState:
        """Format agent output as JSON for frontend and return updated state."""
        agent_output = state.get("output", "No output available")
        
        # Check if this is the end of the conversation
        should_end = False
        if state.get("current_agent") == "end":
            should_end = True
        
        # Also check output for end conversation indicators
        end_phrases = ["goodbye", "bye", "thanks", "thank you", "exit", "quit", "end conversation"]
        if any(phrase in agent_output.lower() for phrase in end_phrases):
            should_end = True
        
        # Generate structured JSON for frontend
        output_data = self._display_output_to_human(agent_output, state)
        
        # If ending, add a flag to the output data
        if should_end:
            output_data["conversation_ended"] = True
        
        # Return the updated state with output_data and should_end flag
        return {**state, "output_data": output_data, "should_end": should_end}

    def _get_human_feedback(self):
        """Get feedback from the human."""
        # In a real application, this would be handled by the UI
        # For console-based testing:
        feedback = input("Your response (leave empty to end conversation): ")
        if feedback.strip() == "":
            return None
        return feedback

    def _display_output_to_human(self, output: str, state: AgentState) -> Dict[str, Any]:
        """Format the agent's output as JSON for the frontend."""
        # Extract any structured data from the output
        structured_data = self._extract_structured_data(output)

        # Create a response object that can be consumed by the frontend
        response = {
        "type": "agent_response",
        "text_content": output,
        "structured_data": structured_data,
        "timestamp": datetime.now().isoformat(),
        "agent_type": state.get("current_agent", "unknown"),
        "requires_feedback": True,
        "conversation_id": hash(tuple(str(m) for m in self.messages)) % 10000  # Simple unique ID
        }
        
        # For debugging only
        print(f"Agent response: {output[:100]}...")
        
        return response

    def _extract_structured_data(self, output: str) -> Dict[str, Any]:
        """Extract structured data from agent output text."""
        data = {
            "detected_entities": [],
            "warnings": [],
            "suggestions": []
        }
        
        # Extract shopping items if present
        import re
        list_items = re.findall(r'[-•]\s*([^\n]+)', output)
        if list_items:
            data["detected_entities"] = [{"type": "list_item", "value": item.strip()} for item in list_items]
        
        # Extract warnings
        warnings = re.findall(r'⚠️([^\n]+)|Warning:([^\n]+)', output)
        if warnings:
            data["warnings"] = [w[0] or w[1] for w in warnings]
        
        # Extract prices or budget information
        prices = re.findall(r'\$(\d+\.\d{2})', output)
        if prices:
            data["price_mentions"] = [float(price) for price in prices]
        
        # Try to identify if this is a shopping list
        if any(keyword in output.lower() for keyword in ["shopping list", "items to buy", "purchase"]):
            data["content_type"] = "shopping_list"
        # Check if it's a recipe
        elif any(keyword in output.lower() for keyword in ["recipe", "ingredients", "instructions"]):
            data["content_type"] = "recipe"
        # Check if it's a cart update
        elif any(keyword in output.lower() for keyword in ["cart", "added", "removed", "updated"]):
            data["content_type"] = "cart_update"
        else:
            data["content_type"] = "general_response"
        
        return data

    #Core Router of SuperAgent...........................................................................
    def _route_to_agent(self, state: AgentState) -> AgentState:
        """Route the message to the appropriate agent with enhanced context understanding."""
        if not state["messages"]:
            return {"current_agent": "shopping-list", **state}
        
        message = state["messages"][-1]
        message_content = message.content if hasattr(message, "content") else str(message)
        
        # Get conversation context from recent messages
        recent_messages = list(self.messages)[-3:]  # Last 3 messages for context
        context = "\n".join([f"User: {msg.content}" for msg in recent_messages if hasattr(msg, 'content')])
        
        # Enhanced routing prompt with examples
        prompt = PromptTemplate(
            template="""Analyze the user message and conversation context to determine the best agent:

    Context (recent conversation):
    {context}

    Current message: {message}

    Choose the appropriate agent:

    1. SHOPPING-LIST AGENT: For creating, managing, or updating shopping lists, meal planning, 
    adding items to lists, organizing groceries, dietary requirements
    Examples: "Add milk to my list", "Create a weekly meal plan", "I need ingredients for pasta"

    2. CART-MANAGER AGENT: For managing shopping cart operations like adding/removing items,
    viewing cart contents, checkout processes, modifying quantities
    Examples: "Add 2 apples to cart", "Remove bread from cart", "Show my cart", "Update quantity"

    3. RECIPE-SHOPPING AGENT: For finding recipes, getting cooking instructions, recipe recommendations,
    ingredient substitutions, cooking tips
    Examples: "Find a recipe for dinner", "How do I make lasagna?", "Suggest vegetarian recipes"
    
    4. If unsure, default to the shopping list agent.
    
    5. If user wants to end the conversation, respond with "END".

    Respond with just the agent name: shopping-list, cart-manager, or recipe-shopping or END """,
            input_variables=["message", "context"]
        )
        
        formatted_prompt = prompt.format(message=message_content, context=context)
        response = llm.predict(formatted_prompt).strip().lower()
        
        # Parse response more robustly
        if "shopping-list" in response or "shopping" in response:
            current_agent = "shopping-list"
        elif "cart-manager" in response or "cart" in response:
            current_agent = "cart-manager"
        elif "recipe-shopping" in response or "recipe" in response:
            current_agent = "recipe-shopping"
        elif "end" in response or "END" in response or "stop" in response:
            current_agent = "end"
        else:
            # Fallback routing based on keywords
            message_lower = message_content.lower()
            if any(word in message_lower for word in ["cart", "add to cart", "remove from cart", "checkout"]):
                current_agent = "cart-manager"
            elif any(word in message_lower for word in ["recipe", "cook", "ingredient", "how to make"]):
                current_agent = "recipe-shopping"
            else:
                current_agent = "shopping-list"  # Default
        
        return {**state, "current_agent": current_agent}
    # Specialized agent methods..................................................................................
    
    def _run_shopping_list_agent(self, state: AgentState) -> AgentState:
        """Run the shopping list agent."""
        message = state["messages"][-1]
        message_content = message.content if hasattr(message, "content") else str(message)
        
        response = self.shopping_list_agent.invoke({
            "input": message_content,
            "agent_scratchpad": ""
        })
        
        return {**state, "output": response["output"]}
    
    def _run_cart_manager_agent(self, state: AgentState) -> AgentState:
        """Run the cart manager agent."""
        message = state["messages"][-1]
        message_content = message.content if hasattr(message, "content") else str(message)
        
        response = self.cart_manager_agent.run_cart_manager(message_content, state["user_id"], self.cart_manager_agent)
        
        return {**state, "output": response}
    
    def _run_recipe_agent(self, state: AgentState) -> AgentState:
        """Run the recipe shopping agent."""
        message = state["messages"][-1]
        message_content = message.content if hasattr(message, "content") else str(message)
        
        response = self.recipe_agent.invoke({
            "input": message_content,
            "agent_scratchpad": ""
        })
        
        return {**state, "output": response["output"]}
    
    
    # Message handling methods..................................................................................
    
    def add_message(self, message: BaseMessage):
        """Add a message to the queue."""
        self.messages.append(message)
    
    def process_message(self, message: str) -> Dict[str, Any]:
        """Process a message through the agent workflow and return JSON response."""
        # Create a human message from the input string
        human_message = HumanMessage(content=message)
        
        # Add the message to the queue
        self.add_message(human_message)
        
        # Initialize the state for the workflow
        initial_state = AgentState(
            messages=list(self.messages),  # Convert deque to list
            user_id=self.user_id,
            current_agent=None,
            output=None,
            output_data=None  # Add output_data field
        )
        
        # Run the workflow
        final_state = self.workflow.invoke(initial_state)
        
        # Return the structured JSON response
        if "output_data" in final_state and final_state["output_data"]:
            return final_state["output_data"]
        else:
            # Fallback if output_data wasn't set
            return {
                "type": "agent_response",
                "text_content": final_state.get("output", "No output generated"),
                "structured_data": {},
                "timestamp": datetime.now().isoformat(),
                "agent_type": final_state.get("current_agent", "unknown"),
                "requires_feedback": True,
                "conversation_id": hash(tuple(str(m) for m in self.messages)) % 10000
            }
    
   
