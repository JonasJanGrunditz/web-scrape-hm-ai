from openai import OpenAI
from pydantic import BaseModel
client = OpenAI(api_key="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")        # assumes OPENAI_API_KEY is set




class RecommendedArticles(BaseModel):
    recommended_articles: list[str]

response = client.responses.parse(
    model="gpt-4o-mini",
    input=f"""Each garment in the database has an Article ID which consist of digits, example:1222124007 . Give me recommendations of a blue cloths""",
    tools=[{
        "type": "file_search",
        "vector_store_ids": ["vs_683da4cb755c819187853dee0e775957"],
        "max_num_results": 5
    }],
    text_format=RecommendedArticles,
)
print(response.output_parsed.)

