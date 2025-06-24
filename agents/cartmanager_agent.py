from typing import Dict, Any, Optional
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import tool
from langchain.agents import AgentExecutor, create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from backend.app import schemas, database
from backend.app.routers.cart import (
    add_to_cart,
    update_cart_item,
    remove_product_from_cart,
    get_cart,
    checkout,
    get_user_by_id  # you need to define this helper
)
import json
import logging

# Setup logging
logger = logging.getLogger(__name__)

# -------------------------------
# 🛠️ Agent Tools
# -------------------------------

def get_db_session():
    """Helper function to get database session with proper error handling"""
    db_gen = database.get_db()
    try:
        return next(db_gen)
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise

@tool
def agent_cart_adder(cart_item: str, user_id: int) -> str:
    """
    Add an item to the user's cart.
    
    Args:
        cart_item: JSON string containing cart item details (product_id, quantity, etc.)
        user_id: ID of the user
        
    Returns:
        JSON string with operation result
    """
    try:
        # Parse cart_item if it's a string
        if isinstance(cart_item, str):
            cart_data = json.loads(cart_item)
        else:
            cart_data = cart_item
            
        db = get_db_session()
        try:
            user = get_user_by_id(user_id, db)
            if not user:
                return json.dumps({"error": "User not found", "success": False})
                
            cart_obj = schemas.CartCreate(**cart_data)
            result = add_to_cart(cart_item=cart_obj, db=db, current_user=user)
            return json.dumps({"result": result, "success": True})
        finally:
            db.close()
            
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON format: {e}", "success": False})
    except Exception as e:
        logger.error(f"Error adding to cart: {e}")
        return json.dumps({"error": str(e), "success": False})

@tool
def agent_update_cart_item(product_id: int, cart_item: str, user_id: int) -> str:
    """
    Update a cart item.
    
    Args:
        product_id: ID of the product to update
        cart_item: JSON string containing updated cart item details
        user_id: ID of the user
        
    Returns:
        JSON string with operation result
    """
    try:
        if isinstance(cart_item, str):
            cart_data = json.loads(cart_item)
        else:
            cart_data = cart_item
            
        db = get_db_session()
        try:
            user = get_user_by_id(user_id, db)
            if not user:
                return json.dumps({"error": "User not found", "success": False})
                
            cart_obj = schemas.CartCreate(**cart_data)
            result = update_cart_item(product_id=product_id, cart_item=cart_obj, db=db, current_user=user)
            return json.dumps({"result": result, "success": True})
        finally:
            db.close()
            
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON format: {e}", "success": False})
    except Exception as e:
        logger.error(f"Error updating cart item: {e}")
        return json.dumps({"error": str(e), "success": False})

@tool
def agent_delete_cart_item(product_id: int, user_id: int) -> str:
    """
    Delete an item from the cart.
    
    Args:
        product_id: ID of the product to remove
        user_id: ID of the user
        
    Returns:
        JSON string with operation result
    """
    try:
        db = get_db_session()
        try:
            user = get_user_by_id(user_id, db)
            if not user:
                return json.dumps({"error": "User not found", "success": False})
                
            result = remove_product_from_cart(product_id=product_id, db=db, current_user=user)
            return json.dumps({"result": result, "success": True})
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error deleting cart item: {e}")
        return json.dumps({"error": str(e), "success": False})

@tool
def agent_get_cart(user_id: int) -> str:
    """
    Retrieve current cart contents.
    
    Args:
        user_id: ID of the user
        
    Returns:
        JSON string with cart contents
    """
    try:
        db = get_db_session()
        try:
            user = get_user_by_id(user_id, db)
            if not user:
                return json.dumps({"error": "User not found", "success": False})
                
            result = get_cart(db=db, current_user=user)
            return json.dumps({"cart": result, "success": True})
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error retrieving cart: {e}")
        return json.dumps({"error": str(e), "success": False})

@tool
def agent_order(address: str, total_amount: float, user_id: int) -> str:
    """
    Place an order and handle checkout.
    
    Args:
        address: Delivery address
        total_amount: Total amount for the order
        user_id: ID of the user
        
    Returns:
        JSON string with order result
    """
    try:
        db = get_db_session()
        try:
            user = get_user_by_id(user_id, db)
            if not user:
                return json.dumps({"error": "User not found", "success": False})
                
            result = checkout(address=address, total_amount=total_amount, db=db, current_user=user)
            return json.dumps({"order": result, "success": True})
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error processing order: {e}")
        return json.dumps({"error": str(e), "success": False})

# List of available tools
tools = [
    agent_cart_adder,
    agent_update_cart_item,
    agent_delete_cart_item,
    agent_get_cart,
    agent_order
]

# -------------------------------
# 🧠 Enhanced PromptTemplate
# -------------------------------
prompt = PromptTemplate(
    input_variables=["input", "agent_scratchpad", "tools", "tool_names"],
    template="""
You are VoiceCart, an intelligent shopping assistant that helps users manage their shopping experience through natural conversation.

Your capabilities include:
1. 🛒 Add items to cart - Help users add products with proper quantities
2. ✏️ Update cart items - Modify quantities or product details
3. 🗑️ Remove items from cart - Delete unwanted products
4. 👀 View cart contents - Show current cart with totals
5. 🚚 Process checkout - Handle order placement with delivery details

IMPORTANT GUIDELINES:
- Always be helpful, friendly, and conversational
- When users mention products, ask for clarification if needed (product ID, quantity, etc.)
- For cart operations, ensure you have the user_id (this should be provided in the context)
- Handle errors gracefully and provide clear feedback
- For checkout, confirm the address and total amount before processing
- Use natural language responses, not just technical outputs

Available tools: {tools}

Use this format for your reasoning:
Question: the user's request
Thought: analyze what the user wants and plan your approach
Action: choose the appropriate tool from [{tool_names}]
Action Input: provide the required parameters for the tool
Observation: review the tool's response
... (repeat Thought/Action/Action Input/Observation as needed)
Thought: I now understand the situation and can provide a final response
Final Answer: provide a helpful, conversational response to the user

Current user request: {input}
{agent_scratchpad}
"""
)

# -------------------------------
# 🤖 Agent Initializer
# -------------------------------
def initialize_cart_manager_agent(api_key: Optional[str] = None, model: str = "gemini-pro") -> AgentExecutor:
    """
    Initialize the VoiceCart agent with proper configuration.
    
    Args:
        api_key: Google API key (optional if set in environment)
        model: Gemini model to use
        
    Returns:
        Configured AgentExecutor
    """
    try:
        # Initialize LLM with better parameters
        llm_kwargs = {
            "model": model,
            "temperature": 0.2,  # Slightly lower for more consistent responses
            "max_output_tokens": 1024,
        }
        
        if api_key:
            llm_kwargs["google_api_key"] = api_key
            
        llm = ChatGoogleGenerativeAI(**llm_kwargs)
        
        # Create the agent
        agent = create_react_agent(
            llm=llm,
            tools=tools,
            prompt=prompt
        )
        
        # Create executor with enhanced configuration
        executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            max_iterations=10,
            early_stopping_method="generate",
            handle_parsing_errors=True,
            return_intermediate_steps=True
        )
        
        return executor
        
    except Exception as e:
        logger.error(f"Error initializing agent: {e}")
        raise

# -------------------------------
# 🎯 Usage Example
# -------------------------------
def chat_with_voicecart(user_input: str, user_id: int, agent_executor: AgentExecutor) -> Dict[str, Any]:
    """
    Process user input through the VoiceCart agent.
    
    Args:
        user_input: User's natural language request
        user_id: ID of the current user
        agent_executor: Initialized agent executor
        
    Returns:
        Dictionary with response and metadata
    """
    try:
        # Add user context to the input
        contextual_input = f"User ID: {user_id}\nRequest: {user_input}"
        
        # Execute the agent
        response = agent_executor.invoke({"input": contextual_input})
        
        return {
            "response": response["output"],
            "success": True,
            "intermediate_steps": response.get("intermediate_steps", [])
        }
        
    except Exception as e:
        logger.error(f"Error in chat processing: {e}")
        return {
            "response": "I'm sorry, I encountered an error processing your request. Please try again.",
            "success": False,
            "error": str(e)
        }

# Example usage:
# agent = initialize_cart_manager_agent()
# result = chat_with_voicecart("Add 2 iPhone 14s to my cart", user_id=123, agent_executor=agent)