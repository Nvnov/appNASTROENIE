
# config.py
from dotenv import load_dotenv
import os

load_dotenv()
VK_API_TOKEN = os.getenv("VK_API_TOKEN")

if not VK_API_TOKEN:
    raise ValueError("VK_API_TOKEN not found in .env file")
