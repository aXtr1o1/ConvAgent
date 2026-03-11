import os
from dotenv import load_dotenv
from openai import AzureOpenAI
from supabase import create_client

load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
secKey = os.getenv("SECRET_KEY")
pubKey = os.getenv("PUBLIC_KEY")

azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
azure_key = os.getenv("AZURE_OPENAI_KEY")
azure_version = os.getenv("AZURE_OPENAI_VERSION")
azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

db = create_client(supabase_url, secKey)

# Azure OpenAI client
client = AzureOpenAI(
    api_key=azure_key,
    api_version=azure_version,
    azure_endpoint=azure_endpoint
)