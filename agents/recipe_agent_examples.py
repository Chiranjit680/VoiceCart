"""
Example usage of the Recipe Shopping Agent
"""

from recipe_shopping_agent import build_recipe_agent

def test_recipe_agent():
    """Test the recipe agent with various scenarios"""
    
    agent = build_recipe_agent()
    
    # Test scenarios
    test_cases = [
        {
            "name": "Recipe for specific number of people",
            "input": "I want to make chicken alfredo pasta for 8 people. Can you find a recipe and give me the complete ingredient list?"
        },
        {
            "name": "Recipe search and shopping list",
            "input": "Find me a healthy vegetarian dinner recipe for 4 people and create a shopping list"
        },
        {
            "name": "Recipe from available ingredients",
            "input": "I have chicken, rice, onions, and tomatoes. What can I make for 3 people?"
        },
        {
            "name": "Complete meal planning",
            "input": "I need to cook dinner for 6 people. I want something with beef that takes less than 30 minutes. Give me the recipe and shopping list."
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"TEST CASE {i}: {test_case['name']}")
        print(f"{'='*60}")
        print(f"INPUT: {test_case['input']}")
        print(f"{'='*60}")
        
        try:
            response = agent.invoke({
                "input": test_case['input'],
                "agent_scratchpad": ""
            })
            
            print("RESPONSE:")
            print(response["output"])
            
        except Exception as e:
            print(f"ERROR: {str(e)}")
        
        print(f"{'='*60}")
        input("Press Enter to continue to next test case...")

if __name__ == "__main__":
    print("Testing Recipe Shopping Agent...")
    print("Make sure you have set up your SPOONACULAR_API_KEY in your .env file")
    
    # You can run individual tests or all tests
    choice = input("Run all tests? (y/n): ").lower().strip()
    
    if choice == 'y':
        test_recipe_agent()
    else:
        # Run a single quick test
        agent = build_recipe_agent()
        user_input = input("Enter your recipe request: ")
        
        response = agent.invoke({
            "input": user_input,
            "agent_scratchpad": ""
        })
        
        print("\nRESPONSE:")
        print(response["output"])