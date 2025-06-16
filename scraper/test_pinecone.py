import io
import os
import requests
import json
from dotenv import load_dotenv
from openai import OpenAI
from elasticsearch_client import GarmentsElasticsearch
from gcp.gcp_bucket import download_processed_garments_from_gcs
from elasticsearch import Elasticsearch
# Load environment variables
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize Elasticsearch client
def get_elasticsearch_client():
    """Initialize and return Elasticsearch client with API key authentication."""
    api_key = os.getenv("ELASTICSEARCH_API_KEY")
    if not api_key:
        raise ValueError("ELASTICSEARCH_API_KEY not found in environment variables")
    
    # Get Elasticsearch endpoint from environment or use default Elasticsearch Cloud format
    es_endpoint = os.getenv("ELASTICSEARCH_ENDPOINT", "https://my-deployment.es.us-central1.gcp.cloud.es.io:443")
    
    # Create Elasticsearch client with cloud connection
    es = Elasticsearch(
        [es_endpoint],
        api_key=api_key,
        verify_certs=True,
        request_timeout=30,
        retry_on_timeout=True,
        max_retries=3
    )
    
    # Test the connection
    try:
        info = es.info()
        print(f"Connected to Elasticsearch: {info['name']} (version {info['version']['number']})")
        return es
    except Exception as e:
        print(f"Failed to connect to Elasticsearch: {e}")
        print("Please check your ELASTICSEARCH_ENDPOINT and ELASTICSEARCH_API_KEY")
        raise

def create_garments_index(es_client, index_name="hm_garments"):
    """Create an Elasticsearch index for garments data with proper mapping."""
    # Define the mapping for the garments index
    mapping = {
        "mappings": {
            "properties": {
                "article_id": {"type": "keyword"},
                "sizes_availability": {"type": "text", "analyzer": "standard"},
                "description": {"type": "text", "analyzer": "standard"},
                "material": {"type": "text", "analyzer": "standard"},
                "category": {"type": "keyword"},
                "color": {"type": "keyword"},
                "attributes": {"type": "text", "analyzer": "standard"},
                "discounted_price": {"type": "float"},
                "original_price": {"type": "float"},
                "discount_percentage": {"type": "keyword"},
                "gender": {"type": "keyword"},
                "created_at": {"type": "date"}
            }
        }
    }
    
    # Create index if it doesn't exist
    if not es_client.indices.exists(index=index_name):
        es_client.indices.create(index=index_name, body=mapping)
        print(f"Created index: {index_name}")
    else:
        print(f"Index {index_name} already exists")

def upload_garments_to_elasticsearch(garments_data, es_client, index_name="hm_garments"):
    """Upload garments data to Elasticsearch for keyword searching."""
    from datetime import datetime
    
    print(f"Uploading {len(garments_data)} garments to Elasticsearch...")
    
    # Prepare bulk upload data
    bulk_data = []
    for garment in garments_data:
        # Clean and prepare the data
        doc = garment.copy()
        
        # Convert price strings to floats
        try:
            doc['discounted_price'] = float(doc.get('discounted_price', 0))
        except (ValueError, TypeError):
            doc['discounted_price'] = 0.0
            
        try:
            doc['original_price'] = float(doc.get('original_price', 0))
        except (ValueError, TypeError):
            doc['original_price'] = 0.0
        
        # Add timestamp
        doc['created_at'] = datetime.now().isoformat()
        
        # Add to bulk data
        bulk_data.append({
            "index": {
                "_index": index_name,
                "_id": doc['article_id']  # Use article_id as document ID
            }
        })
        bulk_data.append(doc)
    
    # Perform bulk upload
    try:
        response = es_client.bulk(body=bulk_data)
        
        # Check for errors
        if response['errors']:
            print("Some documents failed to upload:")
            for item in response['items']:
                if 'index' in item and 'error' in item['index']:
                    print(f"Error uploading {item['index']['_id']}: {item['index']['error']}")
        else:
            print(f"Successfully uploaded {len(garments_data)} garments to Elasticsearch")
            
    except Exception as e:
        print(f"Error uploading to Elasticsearch: {e}")

def search_garments(es_client, query, index_name="hm_garments", size=10):
    """Search garments by keywords in Elasticsearch."""
    search_body = {
        "query": {
            "multi_match": {
                "query": query,
                "fields": [
                    "description^3",  # Give description higher weight
                    "category^2",     # Give category medium weight
                    "attributes^2",   # Give attributes medium weight
                    "material",
                    "color",
                    "sizes_availability"
                ],
                "type": "best_fields",
                "fuzziness": "AUTO"
            }
        },
        "highlight": {
            "fields": {
                "description": {},
                "attributes": {},
                "material": {},
                "category": {}
            }
        },
        "size": size
    }
    
    try:
        response = es_client.search(index=index_name, body=search_body)
        return response
    except Exception as e:
        print(f"Error searching Elasticsearch: {e}")
        return None

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

# Download and process the garment data
raw_garment_data = download_processed_garments_from_gcs()[:50]

# Parse into structured format
structured_garments = parse_garments_to_structured_format(raw_garment_data)
print(f"Parsed {len(structured_garments)} garments")
unique_garments_dict = {garment.get('article_id'): garment for garment in structured_garments if garment.get('article_id')}
structured_garments = list(unique_garments_dict.values())
print(f"Unique garments after deduplication: {len(structured_garments)}")
print(structured_garments[:2])  # Print the first garment for verification
print(f"Parsed {len(structured_garments)} garments")

# Upload to Elasticsearch for keyword searching
try:
    # Initialize Elasticsearch client
    es_client = get_elasticsearch_client()
    
    # Create the garments index with proper mapping
    create_garments_index(es_client)
    
    # Upload the structured garments data
    upload_garments_to_elasticsearch(structured_garments, es_client)
    
    # Example search functionality
    print("\n--- Example Search Results ---")
    search_results = search_garments(es_client, "shaping microfiber", size=3)
    
    if search_results and search_results['hits']['total']['value'] > 0:
        print(f"Found {search_results['hits']['total']['value']} results for 'shaping microfiber':")
        for hit in search_results['hits']['hits']:
            garment = hit['_source']
            score = hit['_score']
            print(f"\nScore: {score}")
            print(f"Article ID: {garment['article_id']}")
            print(f"Category: {garment['category']}")
            print(f"Description: {garment['description'][:100]}...")
            print(f"Color: {garment['color']}")
            print(f"Price: {garment['discounted_price']}")
            
            # Show highlights if available
            if 'highlight' in hit:
                print("Highlighted matches:")
                for field, highlights in hit['highlight'].items():
                    print(f"  {field}: {highlights[0]}")
    else:
        print("No search results found")
        
    print("\n--- Search Functions Available ---")
    print("You can now search garments using:")
    print("search_results = search_garments(es_client, 'your search query')")
    print("Common search examples:")
    print("- search_garments(es_client, 'microfiber shaping')")
    print("- search_garments(es_client, 'high waist cotton')")
    print("- search_garments(es_client, 'beige seamless')")
    print("- search_garments(es_client, 'DAM trosor')")
    
except Exception as e:
    print(f"Error setting up Elasticsearch: {e}")
    print("Please check your Elasticsearch configuration and API key")