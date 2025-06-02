from openai import OpenAI
from pydantic import BaseModel
class ArticleSummary(BaseModel):
    article_id: int
    sizes_and_availability: str
    beskrivning_och_passform: str
    material: str

def extract_sections_from_markdown_openai(markdown_content: str, client) -> str:
    """
    Extracts text under the 'Beskrivning och passform' and "MATERIAL" sections from the provided markdown content.
    
    Args:
        markdown_content (str): The markdown content to analyze.
        
    Returns:
        str: The extracted text as returned by the OpenAI GPT-4 Mini model.
    """
    # Set your OpenAI API key


    response = client.responses.parse(
    model="gpt-4o-mini",
    input=f""" Structure and clean the text so it is easy for the GenAI Agent to search for the data in a vector database
                
                Output structure:
                'article_id': 'Is digits, usually coming after Art.nr: 1259098002'
                'sizes_and_availability': 'Text',
                'beskrivning_och_passform': 'Text',
                'material': 'Text',
                
            
                Please extract the above sections from the markdown content:
            {markdown_content}
            """,
    text_format=ArticleSummary,
)
    
    
    
    return f"""Article ID: {response.output_parsed.article_id}
    Sizes & Availability: {response.output_parsed.sizes_and_availability}
    Description & Fit: {response.output_parsed.beskrivning_och_passform}
    Material: {response.output_parsed.material}
    """
