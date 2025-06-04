import io
import os
import requests
from dotenv import load_dotenv
from openai import OpenAI
from gcp.gcp_bucket import download_processed_garments_from_gcs

# Load environment variables
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))        # assumes OPENAI_API_KEY is set
                          # or client = OpenAI(api_key="sk-…")

def create_file(client, data, *, filename="data.txt"):
    """
    data can be:
      • a URL (http/https)
      • a local file path
      • a list/tuple of strings                  <-- NEW
    """
    # 1. URL ------------------------------------------------------------------
    if isinstance(data, str) and (data.startswith("http://") or data.startswith("https://")):
        response = requests.get(data)
        response.raise_for_status()
        file_obj   = io.BytesIO(response.content)
        file_tuple = (data.split('/')[-1] or filename, file_obj)

    # 2. Local path -----------------------------------------------------------
    elif isinstance(data, str):
        file_obj   = open(data, "rb")                     # will be closed by openai-python
        file_tuple = (data.split('/')[-1], file_obj)

    # 3. List/tuple of strings -----------------------------------------------
    elif isinstance(data, (list, tuple)):
        joined     = "\n".join(map(str, data))            # join however you like
        file_obj   = io.BytesIO(joined.encode("utf-8"))
        file_tuple = (filename, file_obj)

    else:
        raise TypeError("data must be a URL, a local path, or a list/tuple of strings")

    # Upload
    result = client.files.create(
        file=file_tuple,
        purpose="assistants"
    )
    print("Uploaded file id:", result.id)
    return result.id




def parse_garments_to_structured_format(garment_data):
    """
    Parse the flat garment data list into structured format to prevent misattribution.
    Each garment will be a self-contained JSON object.
    """
    structured_garments = []
    current_garment = {}
    
    for item in garment_data:
        item = item.strip()
        
        # Skip empty strings (separators)
        if not item:
            if current_garment:
                # Complete the current garment and add to list
                structured_garments.append(current_garment)
                current_garment = {}
            continue
            
        # Parse each field
        if item.startswith('Article ID:'):
            current_garment['article_id'] = item.replace('Article ID:', '').strip()
        elif item.startswith('Sizes & Availability:'):
            current_garment['sizes_availability'] = item.replace('Sizes & Availability:', '').strip()
        elif item.startswith('Description & Fit:'):
            current_garment['description'] = item.replace('Description & Fit:', '').strip()
        elif item.startswith('Material:'):
            current_garment['material'] = item.replace('Material:', '').strip()
        elif item.startswith('Category:'):
            current_garment['category'] = item.replace('Category:', '').strip()
        elif item.startswith('Color:'):
            current_garment['color'] = item.replace('Color:', '').strip()
        elif item.startswith('Attributes:'):
            current_garment['attributes'] = item.replace('Attributes:', '').strip()
        elif item.startswith('Discounted Price:'):
            current_garment['discounted_price'] = item.replace('Discounted Price:', '').strip()
        elif item.startswith('Original Price:'):
            current_garment['original_price'] = item.replace('Original Price:', '').strip()
        elif item.startswith('Discount Percentage:'):
            current_garment['discount_percentage'] = item.replace('Discount Percentage:', '').strip()
        elif item.startswith('Gender:'):
            current_garment['gender'] = item.replace('Gender:', '').strip()
    
    # Don't forget the last garment if the list doesn't end with empty string
    if current_garment:
        structured_garments.append(current_garment)
    
    return structured_garments

def format_garments_for_vector_store(structured_garments):
    """
    Format structured garments into clear, delimited text entries.
    Each garment is a complete, self-contained entry with clear boundaries.
    """
    formatted_entries = []
    
    for garment in structured_garments:
        # Create a well-structured text block for each garment
        entry = f"""
=== GARMENT ENTRY START ===
Article ID: {garment.get('article_id', 'N/A')}
Category: {garment.get('category', 'N/A')}
Color: {garment.get('color', 'N/A')}
Description: {garment.get('description', 'N/A')}
Material: {garment.get('material', 'N/A')}
Sizes & Availability: {garment.get('sizes_availability', 'N/A')}
Attributes: {garment.get('attributes', 'N/A')}
Discounted Price: {garment.get('discounted_price', 'N/A')}
Original Price: {garment.get('original_price', 'N/A')}
Discount Percentage: {garment.get('discount_percentage', 'N/A')}
Gender: {garment.get('gender', 'N/A')}
=== GARMENT ENTRY END ===
"""
        formatted_entries.append(entry.strip())
    
    return formatted_entries

# Download and process the garment data
raw_garment_data = download_processed_garments_from_gcs()

# Parse into structured format
structured_garments = parse_garments_to_structured_format(raw_garment_data)
print(f"Parsed {len(structured_garments)} garments")

# Format for vector store with clear delimiters
formatted_garment_data = format_garments_for_vector_store(structured_garments)

file_id = create_file(client, formatted_garment_data, filename="structured_garments_corpus.txt")


vector_store = client.vector_stores.create(
    name="structured_fashion_knowledge_base_v2",
)
print(vector_store.id)


client.vector_stores.files.create(
    vector_store_id=vector_store.id,
    file_id=file_id
)
result = client.vector_stores.files.list(
    vector_store_id=vector_store.id
)
print(result)