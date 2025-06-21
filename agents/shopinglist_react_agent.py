from typing import Any, Dict, List
from langchain_core.messages import BaseMessage
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import tool
from langchain.agents import AgentExecutor, create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os
import json
from dummydb import products_db
# Add these lines at the top of your file
import sys
import os

# Add the parent directory to the path to find modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

# Now try importing your module
from utils.json_formatters import beautify_json

# Rest of your imports and code follows...
load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")

# ------------------ Allergy keyword DB --------------------
allergen_keywords = {
    "nuts": ["peanut", "almond", "walnut", "cashew", "pecan", "hazelnut", "pistachio", "tree nuts"],
    "dairy": ["milk", "cheese", "butter", "cream", "lactose", "casein", "whey"],
    "gluten": ["wheat", "barley", "rye", "oats", "gluten"],
    "eggs": ["egg", "albumin", "lecithin"],
    "soy": ["soy", "soybean", "tofu", "tempeh"],
    "shellfish": ["shrimp", "crab", "lobster", "shellfish"],
    "fish": ["salmon", "tuna", "cod", "fish"],
    "sesame": ["sesame", "tahini"]
}

# ------------------ LLM --------------------
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-exp",
    google_api_key=gemini_api_key,
    temperature=0.7,
    max_output_tokens=1024
)

# ------------------ Tools --------------------
@tool
def check_for_allergies(input_data: str) -> str:
    """
    Check if items in shopping list contain any known allergens.
    Args:
        input_data: JSON string with "shopping_list" and "user_allergies"
        Example: {"shopping_list": ["milk", "eggs"], "user_allergies": ["dairy"]}
    """
    try:
        # Try parsing as JSON
        data = json.loads(input_data)
        shopping_list = data.get("shopping_list", [])
        user_allergies = data.get("user_allergies", [])
    except json.JSONDecodeError:
        # Fallback: try to parse input as strings representing lists
        if isinstance(input_data, str):
            # Try to safely evaluate string representation of lists
            import ast
            parts = input_data.split(",", 1)
            if len(parts) == 2:
                try:
                    shopping_list = ast.literal_eval(parts[0].strip())
                    user_allergies = ast.literal_eval(parts[1].strip())
                except (SyntaxError, ValueError):
                    return "Error: Please provide input as JSON with shopping_list and user_allergies."
            else:
                return "Error: Please provide both shopping_list and user_allergies."
    
    if not isinstance(shopping_list, list) or not isinstance(user_allergies, list):
        return "Error: shopping_list and user_allergies must be lists."
    
    warnings = []
    
    for item in shopping_list:
        item_name = str(item).lower()
        item_warnings = []
        for allergy in user_allergies:
            allergy_keywords = allergen_keywords.get(str(allergy).lower(), [])
            for keyword in allergy_keywords:
                if keyword in item_name:
                    item_warnings.append(allergy)
                    break
        if item_warnings:
            warnings.append(f"⚠️ '{item}' may contain: {', '.join(item_warnings)}")
    
    return "ALLERGEN WARNINGS:\n" + "\n".join(warnings) if warnings else "✅ No allergens detected."


@tool 
def check_budget(input_data: str) -> str:
    """
    Check if the total cost of items in the shopping list exceeds the budget.
    Args:
        input_data: JSON string with "shopping_list" and "budget"
        Example: {"shopping_list": ["milk", "eggs"], "budget": 10.5}
    """
    try:
        # Try parsing as JSON
        data = json.loads(input_data)
        shopping_list = data.get("shopping_list", [])
        budget = float(data.get("budget", 0))
    except json.JSONDecodeError:
        # Fallback: try to parse input as strings representing list and number
        if isinstance(input_data, str):
            import ast
            parts = input_data.split(",", 1)
            if len(parts) == 2:
                try:
                    shopping_list = ast.literal_eval(parts[0].strip())
                    budget = float(parts[1].strip())
                except (SyntaxError, ValueError):
                    return "Error: Please provide input as JSON with shopping_list and budget."
            else:
                return "Error: Please provide both shopping_list and budget."
    
    if not isinstance(shopping_list, list):
        return "Error: shopping_list must be a list."
    
    total_cost = 0.0
    missing_items = []

    for item in shopping_list:
        item_name = str(item).lower()
        if item_name in products_db:
            total_cost += products_db[item_name]["price"]
        else:
            missing_items.append(item)

    if missing_items:
        return f"⚠️ Items not found: {', '.join(missing_items)}"

    if total_cost > budget:
        return f"❌ Budget exceeded! Limit: ${budget}, Cost: ${total_cost:.2f}"
    
    return f"✅ Within budget! Limit: ${budget}, Cost: ${total_cost:.2f}"


@tool
def check_vegan_status(input_data: str) -> str:
    """
    Check if items in shopping list are vegan-friendly.
    Args:
        input_data: JSON string or list of items
        Example: {"shopping_list": ["tofu", "oat milk"]} or ["tofu", "oat milk"]
    """
    try:
        # Try parsing as JSON
        data = json.loads(input_data)
        if isinstance(data, dict):
            shopping_list = data.get("shopping_list", [])
        else:
            shopping_list = data
    except json.JSONDecodeError:
        # Fallback: try to parse input as string representation of a list
        if isinstance(input_data, str):
            import ast
            try:
                shopping_list = ast.literal_eval(input_data)
            except (SyntaxError, ValueError):
                return "Error: Please provide input as JSON with shopping_list or as a list."
    
    if not isinstance(shopping_list, list):
        return "Error: shopping_list must be a list."
    
    non_vegan = []
    for item in shopping_list:
        item_name = str(item).lower()
        if item_name in products_db and not products_db[item_name]["vegan"]:
            non_vegan.append(item)
    
    if non_vegan:
        return f"❌ Not Vegan: {', '.join(non_vegan)}"
    return "✅ All items are vegan-friendly."# Create the list of tools
tools = [check_for_allergies, check_budget, check_vegan_status]

# Get tool descriptions and names for the prompt
tool_descriptions = "\n".join([f"{tool.name}: {tool.description}" for tool in tools])
tool_names = ", ".join([tool.name for tool in tools])

# ReAct agent prompt with properly formatted agent_scratchpad
prompt = PromptTemplate(
    template="""You are VoiceCart, an intelligent shopping assistant. Help users with:

1. Generate shopping lists based on goals (meals, dietary needs, budgets)
2. Check for allergens in shopping items
3. Verify if items are vegan-friendly
4. Ensure budget compliance
5. Provide helpful, friendly, and concise shopping recommendations
6. Provide final answers in a clear, list format
You have access to these tools:
{tools}

Use this format:

Question: the user's request
Thought: your reasoning
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: final result

Question: {input}
{agent_scratchpad}""",
    input_variables=["input", "agent_scratchpad", "tools", "tool_names"]
)

# ------------------ Agent + Executor --------------------
agent = create_react_agent(
    llm=llm,
    tools=tools,
    prompt=prompt
)

agent_exec = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    return_intermediate_steps=True,
    max_iterations=5
)

# ------------------ Test Run --------------------
if __name__ == "__main__":
    response = agent_exec.invoke({
        "input": "Create a vegan shopping list for dinner for $15. Check for nuts and dairy."
    })
    
    print(response["output"])