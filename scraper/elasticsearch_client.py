"""
Elasticsearch client for H&M garments search functionality.
"""
import os
import json
from datetime import datetime
from elasticsearch import Elasticsearch
from dotenv import load_dotenv

load_dotenv()

class GarmentsElasticsearch:
    def __init__(self, index_name="hm_garments"):
        self.index_name = index_name
        self.client = self._get_client()
        
    def _get_client(self):
        """Initialize and return Elasticsearch client with API key authentication."""
        api_key = os.getenv("ELASTICSEARCH_API_KEY")
        if not api_key:
            raise ValueError("ELASTICSEARCH_API_KEY not found in environment variables")
        
        # Get Elasticsearch endpoint from environment
        es_endpoint = os.getenv("ELASTICSEARCH_ENDPOINT")
        if not es_endpoint:
            raise ValueError("ELASTICSEARCH_ENDPOINT not found in environment variables")
        
        # Create Elasticsearch client
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
    
    def create_index(self):
        """Create an Elasticsearch index for garments data with proper mapping."""
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
        if not self.client.indices.exists(index=self.index_name):
            self.client.indices.create(index=self.index_name, body=mapping)
            print(f"Created index: {self.index_name}")
        else:
            print(f"Index {self.index_name} already exists")
    
    def upload_garments(self, garments_data):
        """Upload garments data to Elasticsearch for keyword searching."""
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
                    "_index": self.index_name,
                    "_id": doc['article_id']  # Use article_id as document ID
                }
            })
            bulk_data.append(doc)
        
        # Perform bulk upload
        try:
            response = self.client.bulk(body=bulk_data)
            
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
    
    def search(self, query, size=10, filters=None):
        """Search garments by keywords in Elasticsearch."""
        # Build the base query
        search_body = {
            "query": {
                "bool": {
                    "must": [
                        {
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
                        }
                    ]
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
        
        # Add filters if provided
        if filters:
            filter_clauses = []
            for field, value in filters.items():
                filter_clauses.append({"term": {field: value}})
            
            if filter_clauses:
                search_body["query"]["bool"]["filter"] = filter_clauses
        
        try:
            response = self.client.search(index=self.index_name, body=search_body)
            return response
        except Exception as e:
            print(f"Error searching Elasticsearch: {e}")
            return None
    
    def search_by_category(self, category, size=10):
        """Search garments by category."""
        return self.search("*", size=size, filters={"category": category})
    
    def search_by_gender(self, gender, size=10):
        """Search garments by gender."""
        return self.search("*", size=size, filters={"gender": gender})
    
    def get_all_categories(self):
        """Get all unique categories."""
        agg_body = {
            "aggs": {
                "categories": {
                    "terms": {
                        "field": "category",
                        "size": 100
                    }
                }
            },
            "size": 0
        }
        
        try:
            response = self.client.search(index=self.index_name, body=agg_body)
            categories = [bucket['key'] for bucket in response['aggregations']['categories']['buckets']]
            return categories
        except Exception as e:
            print(f"Error getting categories: {e}")
            return []
    
    def print_search_results(self, search_results, query=""):
        """Pretty print search results."""
        if not search_results or search_results['hits']['total']['value'] == 0:
            print(f"No results found for query: '{query}'")
            return
        
        total = search_results['hits']['total']['value']
        print(f"\nFound {total} results for '{query}':")
        print("=" * 50)
        
        for i, hit in enumerate(search_results['hits']['hits'], 1):
            garment = hit['_source']
            score = hit['_score']
            
            print(f"\n{i}. Article ID: {garment['article_id']} (Score: {score:.2f})")
            print(f"   Category: {garment['category']} | Gender: {garment['gender']}")
            print(f"   Color: {garment['color']}")
            print(f"   Price: {garment['discounted_price']} (was {garment['original_price']})")
            print(f"   Description: {garment['description'][:150]}...")
            
            # Show highlights if available
            if 'highlight' in hit:
                print("   Matches:")
                for field, highlights in hit['highlight'].items():
                    print(f"     {field}: {highlights[0]}")
