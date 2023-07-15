lead_functions = [
    {
        "name": "qualify_lead",
        "description": """Use this function to qualify a lead and retrieve data like name, email, company and industry""",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": f"""
                            User query in plain text
                            """,
                }
            },
            "required": ["query"],
        },
        "name": "retrieve_knowledge",
        "description": """Use this function to read relevant part of the website and provide a summary for the user.
        You should NEVER call this function before qualify_lead has been called in the conversation.""",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": f"""
                            Description of the website in plain text based on the user's query
                            """,
                }
            },
            "required": ["query"],
        },
    }
]