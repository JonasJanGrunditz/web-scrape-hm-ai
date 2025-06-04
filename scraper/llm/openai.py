from openai import OpenAI
from pydantic import BaseModel
class ArticleSummary(BaseModel):
    sizes_and_availability: str
    beskrivning_och_passform: str
    material: str
    category: str
    color: str
    attributes: list[str]

def extract_sections_from_markdown_openai(markdown_content: str, article_id: str, discounted_price: str, original_price: str, discount_percentage: str, gender: str, client) -> str:
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
                'sizes_and_availability': 'Text',
                'beskrivning_och_passform': 'Text',
                'material': 'Text',
                'category': 'the catefory of the garment, e.g. "klänningar"'
                'color': 'the color of the garment, e.g. "svart" . Often exist below Beskrivning'
                'attributes': ['list', 'of', 'attributes', 'e.g. "kortärmad", "långärmad", "v-ringad", "mönstrad"', Passform, Midjehöjd, Längd,Krage, Halsringning, Ärmstil, Ärmlängd and more...]
                
            
                Please extract the above sections from the markdown content:
            {markdown_content}
            """,
    text_format=ArticleSummary,
)
    
    
    
    return f"""Article ID: {article_id}
    Sizes & Availability: {response.output_parsed.sizes_and_availability}
    Description & Fit: {response.output_parsed.beskrivning_och_passform}
    Material: {response.output_parsed.material}
    Category: {response.output_parsed.category}
    Color: {response.output_parsed.color}
    Attributes: {response.output_parsed.attributes}
    Discounted Price: {discounted_price}
    Original Price: {original_price}
    Discount Percentage: {discount_percentage}
    Gender: {gender}
    """
