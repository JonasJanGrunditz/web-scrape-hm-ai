import os
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

# Load environment variables
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))




class RecommendedArticles(BaseModel):
    recommended_articles: list[str]

response = client.responses.parse(
    model="gpt-4.1-2025-04-14",
    input=f"""The Customer is asking for garments to buy.
    Please give suggestions to the customer by looking in the file_search what garments that match the description 
    Output only article ids
    
    The customer is looking for a pair of klänningar""",
    tools=[{
        "type": "file_search",
        "vector_store_ids": ["vs_683da4cb755c819187853dee0e775957"],
        "max_num_results": 5
    }],
    text_format=RecommendedArticles,
)
print(response.output_parsed)

