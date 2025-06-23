from typing import Any, Dict, List, Optional
from langchain_core.messages import BaseMessage
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import tool
from langchain.agents import AgentExecutor, create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os
import json
import requests
import sys
from agent_main import llm

# Add the parent directory to the path to find modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from utils.json_formatters import beautify_json

load_dotenv()
spoonacular_api_key = os.getenv("SPOONACULAR_API_KEY")

if not spoonacular_api_key:
    raise ValueError("SPOONACULAR_API_KEY not found in environment variables")

# Base URL for Spoonacular API
SPOONACULAR_BASE_URL = "https://api.spoonacular.com/recipes"

# ------------------ Recipe Tools --------------------

@tool
def search_recipes(input_data: str) -> str:
    """
    Search for recipes based on a query string.
    Args:
        input_data: JSON string with "query" and optional "number"
        Example: {"query": "chicken pasta", "number": 3}
    Returns:
        JSON string with recipe search results
    """
    try:
        data = json.loads(input_data)
        query = data.get("query", "")
        number = data.get("number", 5)
        
        if not query:
            return "Error: query string is required"
        
        url = f"{SPOONACULAR_BASE_URL}/complexSearch"
        params = {
            "apiKey": spoonacular_api_key,
            "query": query,
            "number": min(number, 100),
            "addRecipeInformation": True,
            "fillIngredients": True
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        if not data.get("results"):
            return f"No recipes found for query: {query}"
        
        # Format the results for better readability
        formatted_results = []
        for recipe in data["results"]:
            formatted_recipe = {
                "id": recipe["id"],
                "title": recipe["title"],
                "readyInMinutes": recipe.get("readyInMinutes", "N/A"),
                "servings": recipe.get("servings", "N/A"),
                "summary": recipe.get("summary", "")[:200] + "..." if recipe.get("summary", "") else "No summary available"
            }
            formatted_results.append(formatted_recipe)
        
        return json.dumps({"recipes": formatted_results}, indent=2)
        
    except requests.exceptions.RequestException as e:
        return f"Error searching recipes: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@tool
def get_recipe_ingredients(input_data: str) -> str:
    """
    Get detailed ingredient list for a specific recipe, scaled for number of people.
    Args:
        input_data: JSON string with "recipe_id" and "servings" 
        Example: {"recipe_id": 12345, "servings": 4}
    Returns:
        Detailed ingredient list with quantities scaled for the specified servings
    """
    try:
        # Parse input data
        data = json.loads(input_data)
        recipe_id = data.get("recipe_id")
        target_servings = data.get("servings", 1)
        
        if not recipe_id:
            return "Error: recipe_id is required"
        
        # Get recipe information
        url = f"{SPOONACULAR_BASE_URL}/{recipe_id}/information"
        params = {
            "apiKey": spoonacular_api_key,
            "includeNutrition": False
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        recipe_data = response.json()
        original_servings = recipe_data.get("servings", 1)
        
        # Calculate scaling factor
        scaling_factor = target_servings / original_servings
        
        # Extract and scale ingredients
        ingredients = recipe_data.get("extendedIngredients", [])
        if not ingredients:
            return f"No ingredients found for recipe ID: {recipe_id}"
        
        scaled_ingredients = []
        for ingredient in ingredients:
            original_amount = ingredient.get("amount", 0)
            scaled_amount = original_amount * scaling_factor
            
            ingredient_info = {
                "name": ingredient.get("name", "Unknown ingredient"),
                "original_amount": original_amount,
                "scaled_amount": round(scaled_amount, 2),
                "unit": ingredient.get("unit", ""),
                "aisle": ingredient.get("aisle", "Unknown aisle")
            }
            scaled_ingredients.append(ingredient_info)
        
        result = {
            "recipe_title": recipe_data.get("title", "Unknown Recipe"),
            "original_servings": original_servings,
            "target_servings": target_servings,
            "scaling_factor": round(scaling_factor, 2),
            "ingredients": scaled_ingredients
        }
        
        return json.dumps(result, indent=2)
        
    except json.JSONDecodeError:
        return "Error: Please provide input as JSON with recipe_id and servings"
    except requests.exceptions.RequestException as e:
        return f"Error fetching recipe: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@tool
def get_recipe_by_ingredients(input_data: str) -> str:
    """
    Find recipes based on available ingredients.
    Args:
        input_data: JSON string with "ingredients" list and optional "number"
        Example: {"ingredients": ["chicken", "rice", "onion"], "number": 3}
    Returns:
        List of recipes that can be made with the given ingredients
    """
    try:
        data = json.loads(input_data)
        ingredients = data.get("ingredients", [])
        number = data.get("number", 5)
        
        if not ingredients:
            return "Error: ingredients list is required"
        
        # Convert ingredients list to comma-separated string
        ingredients_str = ",".join(ingredients)
        
        url = f"{SPOONACULAR_BASE_URL}/findByIngredients"
        params = {
            "apiKey": spoonacular_api_key,
            "ingredients": ingredients_str,
            "number": min(number, 100),
            "ranking": 1,  # Maximize used ingredients
            "ignorePantry": True
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        if not data:
            return f"No recipes found with ingredients: {', '.join(ingredients)}"
        
        # Format results
        formatted_results = []
        for recipe in data:
            formatted_recipe = {
                "id": recipe["id"],
                "title": recipe["title"],
                "used_ingredients": [ing["name"] for ing in recipe.get("usedIngredients", [])],
                "missed_ingredients": [ing["name"] for ing in recipe.get("missedIngredients", [])],
                "unused_ingredients": [ing["name"] for ing in recipe.get("unusedIngredients", [])]
            }
            formatted_results.append(formatted_recipe)
        
        return json.dumps({"recipes": formatted_results}, indent=2)
        
    except json.JSONDecodeError:
        return "Error: Please provide input as JSON with ingredients list"
    except requests.exceptions.RequestException as e:
        return f"Error searching recipes: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@tool
def generate_shopping_list_from_recipe(input_data: str) -> str:
    """
    Generate a complete shopping list from recipe ingredients, organized by grocery store sections.
    Args:
        input_data: JSON string with "recipe_id" and "servings"
        Example: {"recipe_id": 12345, "servings": 4}
    Returns:
        Organized shopping list grouped by store sections
    """
    try:
        # First get the ingredients using the existing tool
        ingredients_result = get_recipe_ingredients(input_data)
        ingredients_data = json.loads(ingredients_result)
        
        if "error" in ingredients_result.lower():
            return ingredients_result
        
        # Organize ingredients by grocery store sections
        shopping_list = {
            "Produce": [],
            "Meat & Seafood": [],
            "Dairy & Eggs": [],
            "Pantry & Dry Goods": [],
            "Frozen": [],
            "Bakery": [],
            "Other": []
        }
        
        # Mapping of common aisles to our categories
        aisle_mapping = {
            "produce": "Produce",
            "meat": "Meat & Seafood",
            "seafood": "Meat & Seafood",
            "dairy": "Dairy & Eggs",
            "eggs": "Dairy & Eggs",
            "milk": "Dairy & Eggs",
            "cheese": "Dairy & Eggs",
            "frozen": "Frozen",
            "bakery": "Bakery",
            "bread": "Bakery",
            "pantry": "Pantry & Dry Goods",
            "canned goods": "Pantry & Dry Goods",
            "condiments": "Pantry & Dry Goods",
            "spices": "Pantry & Dry Goods",
            "baking": "Pantry & Dry Goods"
        }
        
        for ingredient in ingredients_data["ingredients"]:
            aisle = ingredient.get("aisle", "").lower()
            name = ingredient["name"]
            amount = ingredient["scaled_amount"]
            unit = ingredient["unit"]
            
            # Format the ingredient entry
            if amount > 0 and unit:
                item_text = f"{name} ({amount} {unit})"
            elif amount > 0:
                item_text = f"{name} ({amount})"
            else:
                item_text = name
            
            # Determine which section this belongs to
            section = "Other"
            for aisle_key, section_name in aisle_mapping.items():
                if aisle_key in aisle:
                    section = section_name
                    break
            
            shopping_list[section].append(item_text)
        
        # Remove empty sections
        shopping_list = {k: v for k, v in shopping_list.items() if v}
        
        result = {
            "recipe_title": ingredients_data["recipe_title"],
            "servings": ingredients_data["target_servings"],
            "shopping_list": shopping_list,
            "total_items": sum(len(items) for items in shopping_list.values())
        }
        
        return json.dumps(result, indent=2)
        
    except json.JSONDecodeError:
        return "Error: Invalid ingredient data received"
    except Exception as e:
        return f"Error generating shopping list: {str(e)}"


# Create the list of tools
tools = [search_recipes, get_recipe_ingredients, get_recipe_by_ingredients, generate_shopping_list_from_recipe]

# ReAct agent prompt
prompt = PromptTemplate(
    template="""You are RecipeCart, an intelligent recipe and shopping assistant. Help users with:

1. Search for recipes based on their preferences
2. Get detailed ingredient lists scaled for any number of people
3. Find recipes based on available ingredients
4. Generate organized shopping lists from recipes
5. Provide helpful cooking and meal planning advice

You have access to these tools:
{tools}

Use this format:

Question: the user's request
Thought: your reasoning about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action (always use proper JSON format)
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: provide a clear, helpful response with the information requested

Important guidelines:
- Always use proper JSON format for Action Input
- When scaling recipes, make sure to include both recipe_id and servings in the input
- Organize shopping lists in a user-friendly way
- Provide helpful context about recipes (cooking time, difficulty, etc.)
- If a user asks for a recipe for X people, search for recipes first, then get ingredients for the chosen recipe

Question: {input}
{agent_scratchpad}""",
    input_variables=["input", "agent_scratchpad", "tools", "tool_names"]
)

def build_recipe_agent(llm=llm):
    """
    Create a recipe-focused ReAct agent.
    """
    # Get tool descriptions and names for the prompt
    tool_descriptions = "\n".join([f"{tool.name}: {tool.description}" for tool in tools])
    tool_names = ", ".join([tool.name for tool in tools])
    
    agent = create_react_agent(
        llm=llm,
        tools=tools,
        prompt=prompt
    )
    
    agent_exec = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=False,  # Hide intermediate steps
        return_intermediate_steps=False,  # Only return final output
        max_iterations=10,
        handle_parsing_errors=True
    )
    
    return agent_exec

# ------------------ Main Function for testing --------------------
if __name__ == "__main__":
    recipe_agent = build_recipe_agent()
    
    # Test the agent
    response = recipe_agent.invoke({
        "input": "I want to make pancake for 6 people. Can you find a good recipe and give me a complete shopping list?",
        "agent_scratchpad": ""
    })
    
    print("=" * 50)
    print("FINAL RESPONSE:")
    print("=" * 50)
    print(response["output"])