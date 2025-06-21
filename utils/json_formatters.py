import json

def beautify_json(data: str | dict) -> str:
    """
    Takes a JSON string or dictionary and returns a pretty-printed string.
    """
    try:
        if isinstance(data, str):
            parsed = json.loads(data)
        else:
            parsed = data
        return json.dumps(parsed, indent=2, ensure_ascii=False)
    except Exception as e:
        return f"❌ Error formatting JSON: {str(e)}"
