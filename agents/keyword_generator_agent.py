from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from langchain_core.tools import tool
import requests
import os
import re
from typing import List

load_dotenv()

@tool
def get_synonyms(word: str) -> List[str]:
    """
    Get synonyms for a word using the Datamuse API.
    Args:
        word: The input word to find synonyms for.
    Returns:
        A list of similar words.
    """
    try:
        url = f"https://api.datamuse.com/words?ml={word}"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        
        synonyms = [item['word'] for item in resp.json()[:10]]
        return synonyms if synonyms else [word]
    except Exception as e:
        print(f"Error getting synonyms: {e}")
        return [word]

@tool
def get_related_words(word: str) -> List[str]:
    """
    Get words related to the input word using Datamuse API.
    Args:
        word: The input word to find related words for.
    Returns:
        A list of related words.
    """
    try:
        url = f"https://api.datamuse.com/words?rel_trg={word}"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        
        related = [item['word'] for item in resp.json()[:5]]
        return related if related else []
    except Exception as e:
        print(f"Error getting related words: {e}")
        return []

# Initialize Gemini LLM
gemini_api_key = os.getenv("GEMINI_API_KEY")

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=gemini_api_key,
    temperature=0.7,
    max_output_tokens=1024
)

# Define tools
tools = [get_synonyms, get_related_words]

# Updated prompt template for ReAct agent
prompt = PromptTemplate(
    input_variables=["input", "agent_scratchpad", "tools", "tool_names"],
    template="""You are a keyword generation assistant. Your task is to generate 10 similar or related words for the given input word.

Use the available tools to gather different types of related words, then compile a comprehensive list of 10 words.

Available tools: {tools}
Tool names: {tool_names}

Instructions:
1. Use the get_synonyms tool to find synonyms
2. Use get_related_words to find semantically related words
3. Combine the results and select the 10 most relevant words
4. Return ONLY a comma-separated list of words, no quotes, no brackets

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: word1, word2, word3, word4, word5, word6, word7, word8, word9, word10

Question: Generate 10 similar words for: {input}

{agent_scratchpad}""",
)

# Create ReAct agent with tools
agent = create_react_agent(
    llm=llm,
    tools=tools,
    prompt=prompt
)

# Create agent executor with tools
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    max_iterations=10,
    early_stopping_method="generate",
    handle_parsing_errors=True,
    return_intermediate_steps=True
)

def parse_keyword_output(output_text: str) -> List[str]:
    """
    Parse the agent output to extract clean keywords.
    
    Args:
        output_text: Raw output from the agent
        
    Returns:
        List of clean keywords
    """
    if not isinstance(output_text, str):
        return []
    
    # Remove common unwanted characters and patterns
    cleaned = output_text.strip()
    
    # Remove quotes and brackets
    cleaned = re.sub(r'["\'\[\]]', '', cleaned)
    
    # Split by comma and clean each word
    words = [word.strip() for word in cleaned.split(',') if word.strip()]
    
    # Remove duplicates while preserving order
    seen = set()
    unique_words = []
    for word in words:
        word_lower = word.lower()
        if word_lower not in seen and len(word) > 1:
            seen.add(word_lower)
            unique_words.append(word)
    
    return unique_words[:10]  # Limit to 10 words

def generate_keywords(input_text: str) -> List[str]:
    """
    Generate keywords for the given input text.
    
    Args:
        input_text: The word to generate keywords for
        
    Returns:
        List of keywords (strings)
    """
    try:
        response = agent_executor.invoke({"input": input_text})
        output = response.get("output", "")
        
        # Parse the output to get clean keywords
        keywords = parse_keyword_output(output)
        
        # Always include the original word if not already present
        if input_text.lower() not in [kw.lower() for kw in keywords]:
            keywords.append(input_text)
        
        return keywords
        
    except Exception as e:
        print(f"Error generating keywords: {e}")
        # Return fallback keywords
        return [input_text]

def test_keyword_generator():
    """Test the keyword generator with various inputs"""
    
    test_words = ["apple", "computer", "happiness", "running"]
    
    for word in test_words:
        print(f"\n{'='*50}")
        print(f"Testing keyword generation for: '{word}'")
        print('='*50)
        
        result = generate_keywords(word)
        print(type(result))
        
        print(f"\nGenerated keywords:")
        for i, keyword in enumerate(result, 1):
            print(f"  {i}. {keyword}")
        
        print(f"\nTotal keywords generated: {len(result)}")

if __name__ == "__main__":
    # Single test
    input_text = "apple"
    print(f"Generating keywords for '{input_text}'...")
    
    result = generate_keywords(input_text)
    
    print(f"\nGenerated keywords for '{input_text}':")
    print(f"Type: {type(result)}")
    print(f"Keywords: {result}")
    
    # Show clean output
    print(f"\nClean keyword list:")
    for i, keyword in enumerate(result, 1):
        print(f"  {i}. {keyword}")
    
    # Uncomment to run comprehensive tests
    print(f"\n" + "="*50)
    print("Running comprehensive tests...")
    test_keyword_generator()