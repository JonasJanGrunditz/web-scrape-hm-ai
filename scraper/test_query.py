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
    model="gpt-4o-mini",
    input=f"""Each garment in the database has an Article ID which consist of digits, example:1222124007 . Give me recommendations of a blue cloths
    Only output the article ids in a list""",
    tools=[{
        "type": "file_search",
        "vector_store_ids": ["vs_683da4cb755c819187853dee0e775957"],
        "max_num_results": 5
    }],
    text_format=RecommendedArticles,
)
print(response.output_parsed)

