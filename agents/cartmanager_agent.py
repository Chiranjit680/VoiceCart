from typing import Dict, Any, Optional
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import tool
from langchain.agents import AgentExecutor, create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI

import json
import logging
import sys
from dotenv import load_dotenv
import os
load_dotenv()
# Fix the path - go up to VoiceCart, then access backend
current_file = os.path.abspath(__file__)
agents_dir = os.path.dirname(current_file)  # agents directory
voicecart_dir = os.path.dirname(agents_dir)  # VoiceCart directory
project_root = os.path.dirname(voicecart_dir)  # Root directory containing VoiceCart

# Add both paths to sys.path
if voicecart_dir not in sys.path:
    sys.path.insert(0, voicecart_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Now import with the correct relative path
try:
    from backend.app import schemas, database, models
    from backend.app.routers.cart import (
        add_to_cart,
        update_cart_item,
        remove_product_from_cart,
        get_cart,
        checkout
    )
    from backend.app.routers.search import search_products
except ModuleNotFoundError:
    # Alternative import path if the above doesn't work
    try:
        from VoiceCart.backend.app import schemas, database, models
        from VoiceCart.backend.app.routers.cart import (
            add_to_cart,
            update_cart_item,
            remove_product_from_cart,
            get_cart,
            checkout
        )
    except ModuleNotFoundError as e:
        print(f"Import error: {e}")
        print(f"Current directory: {os.getcwd()}")
        print(f"File location: {current_file}")
        print(f"Agents directory: {agents_dir}")
        print(f"VoiceCart directory: {voicecart_dir}")
        print(f"Project root: {project_root}")
        raise ImportError("Could not import required modules. Check your directory structure.")

# Setup logging
logger = logging.getLogger(__name__)

# Add the missing get_user_by_id function
def get_user_by_id(user_id: int, db):
    """Helper function to get user by ID"""
    try:
        return db.query(models.User).filter(models.User.id == user_id).first()
    except Exception as e:
        logger.error(f"Error getting user by ID {user_id}: {e}")
        return None

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
def agent_search_product(product_name: str) -> str:
    """
    Search for products by name.
    
    Args:
        product_name: Name of the product to search for
        
    Returns:
        JSON string with search results
    """
    try:
        db = get_db_session()
        try:
            # Search products by name first
            results = db.query(models.Product).filter(
                models.Product.name.ilike(f"%{product_name}%")
            ).filter(
                models.Product.for_sale == True
            ).limit(10).all()
            
            if not results:
                return json.dumps({"error": "No products found", "success": False})
            
            # Convert products to dictionary format
            products = []
            for product in results:
                # Handle JSON description safely
                description_text = "No description available"
                if product.description:
                    if isinstance(product.description, dict):
                        # If it's already a dict (JSON), extract text
                        description_text = product.description
                    else:
                        # If it's a string
                        description_text = str(product.description)
                
                product_dict = {
                    "id": product.id,
                    "name": product.name,
                    "description": description_text,
                    "price": float(product.price),
                    "stock": product.stock,
                    "brand_name": product.brand_name,
                    "for_sale": product.for_sale
                }
                products.append(product_dict)
            
            return json.dumps({"products": products, "success": True})
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error searching for product: {e}")
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
    agent_order,
    agent_search_product
]

# -------------------------------
# 🧠 Enhanced PromptTemplate
# -------------------------------
prompt = PromptTemplate(
    input_variables=["input", "agent_scratchpad", "tools", "tool_names"],
    template="""
You are VoiceCart, an intelligent shopping assistant that helps users manage their shopping experience through natural conversation.

Your capabilities include:
1. 🔍 Search products - Find products by name or description
2. 🛒 Add items to cart - Help users add products with proper quantities
3. ✏️ Update cart items - Modify quantities or product details
4. 🗑️ Remove items from cart - Delete unwanted products
5. 👀 View cart contents - Show current cart with totals
6. 🚚 Process checkout - Handle order placement with delivery details

IMPORTANT GUIDELINES:
- Always be helpful, friendly, and conversational
- When users mention products without specific IDs, use the search tool first to find products
- After searching, present the options to the user and ask them to choose
- When users mention products, ask for clarification if needed (product ID, quantity, etc.)
- For cart operations, ensure you have the user_id (this should be provided in the context)
- Handle errors gracefully and provide clear feedback
- For checkout, confirm the address and total amount before processing
- Use natural language responses, not just technical outputs

WORKFLOW FOR ADDING PRODUCTS:
1. If user mentions a product name (like "apple", "milk", etc.), first search for it
2. Present the search results with product IDs, names, and prices
3. Ask the user to specify which product they want and the quantity
4. Then add the selected product to cart using the product ID

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
def initialize_cart_manager_agent(api_key: Optional[str] = None, model: str = "gemini-2.5-flash") -> AgentExecutor:
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
def run_cart_manager(user_input: str, user_id: int, agent_executor: AgentExecutor) -> Dict[str, Any]:
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

# test_cartmanager.py
import os
from dotenv import load_dotenv
from agents.cartmanager_agent import initialize_cart_manager_agent, run_cart_manager

# Load environment variables
load_dotenv()

def test_cart_manager():
    """Test the cart manager agent with various scenarios"""
    
    # Initialize the agent
    api_key=os.getenv("GEMINI_API_KEY")
    try:
        agent = initialize_cart_manager_agent(api_key=api_key)
        print("✅ Agent initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")
        return
    
    # Test user ID (replace with a valid user ID from your database)
    test_user_id = 1
    
    # Test scenarios
    test_cases = [
        # "Show me my current cart",
        "Add 2 apples to my cart",
        "Add 1 milk carton  to my cart",
        # "Add 1 milk carton with product ID 5 to my cart",
        # "Update the quantity of product 5 to 3 items",
        # "Remove product 2 from my cart",
        # "I want to checkout with delivery to 123 Main St, total $25.50"
    ]
    
    print("\n🧪 Running test cases...")
    print("=" * 50)
    
    for i, test_input in enumerate(test_cases, 1):
        print(f"\n🔍 Test {i}: {test_input}")
        print("-" * 30)
        
        try:
            result = run_cart_manager(test_input, test_user_id, agent)
            
            if result["success"]:
                print(f"✅ Response: {result['response']}")
                if result.get("intermediate_steps"):
                    print(f"📝 Steps taken: {len(result['intermediate_steps'])} actions")
            else:
                print(f"❌ Error: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ Exception: {e}")
        
        print("-" * 30)

if __name__ == "__main__":
    test_cart_manager()