import os
from dotenv import load_dotenv
from openai import AzureOpenAI
from supabase import create_client

load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
secKey = os.getenv("SECRET_KEY")
pubKey = os.getenv("PUBLIC_KEY")
milvus_host = os.getenv("MILVUS_HOST")
milvus_port = os.getenv("MILVUS_PORT")
azure_emb_endpoint = os.getenv("AZURE_EMBEDDING_ENDPOINT")
azure_emb_key = os.getenv("AZURE_EMBEDDING_KEY")
azure_emb_version = os.getenv("AZURE_EMBEDDING_VERSION")
azure_emb_deployment = os.getenv("AZURE_EMBEDDING_DEPLOYMENT")
azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
azure_key = os.getenv("AZURE_OPENAI_KEY")
azure_version = os.getenv("AZURE_OPENAI_VERSION")
azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
ingest_folder = os.getenv("INGEST_FOLDER")
db = create_client(supabase_url, secKey)

# Azure OpenAI client
client = AzureOpenAI(
    api_key=azure_key,
    api_version=azure_version,
    azure_endpoint=azure_endpoint
)