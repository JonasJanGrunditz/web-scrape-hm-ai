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




garment_data = download_processed_garments_from_gcs()
print(garment_data)


# file_id  = create_file(client, garment_data, filename="my_corpus.txt")


# vector_store = client.vector_stores.create(
#     name="knowledge_base"
# )
# print(vector_store.id)


# client.vector_stores.files.create(
#     vector_store_id=vector_store.id,
#     file_id=file_id
# )
# result = client.vector_stores.files.list(
#     vector_store_id=vector_store.id
# )
# print(result)