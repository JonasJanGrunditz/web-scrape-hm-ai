import os
from dotenv import load_dotenv
from groq import Groq

# Load environment variables
load_dotenv()

def extract_sections_from_markdown(markdown_content: str) -> str:
    """
    Extracts text under the 'Beskrivning och passform' and "MATERIAL" sections from the provided markdown content.
    
    Args:
        markdown_content (str): The markdown content to analyze.
        
    Returns:
        str: The extracted text as returned by the Groq API.
    """
    client = Groq(
        api_key=os.getenv("GROQ_API_KEY"),
    )
    
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": f"""Extract all text under the section 'Beskrivning och passform' and "MATERIAL" from the markdown content.:
There is no need to extract Ytterligare materialinformation
{markdown_content}
""",
            }
        ],
        model="llama-3.3-70b-versatile",
        stream=False,
    )
    
    return chat_completion.choices[0].message.content