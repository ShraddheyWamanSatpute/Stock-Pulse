import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
import sys
from dotenv import load_dotenv

# Ensure we can import from backend
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

from services.pipeline_service import DataPipelineService
from data_extraction.extractors.grow_extractor import GrowwAPIExtractor

async def main():
    mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.getenv("MONGO_DB_NAME", "stockpulse")
    grow_totp_token = os.getenv("GROW_TOTP_TOKEN")
    grow_secret_key = os.getenv("GROW_SECRET_KEY")

    if not grow_totp_token or not grow_secret_key:
        print("Missing GROW_TOTP_TOKEN or GROW_SECRET_KEY in .env")
        return

    print("Connecting to MongoDB...")
    try:
        client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=2000)
        await client.server_info() # Trigger connection error quickly if DB is down
        db = client[db_name]
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
        return

    print("Initializing GrowwAPIExtractor...")
    extractor = GrowwAPIExtractor(db=db, totp_token=grow_totp_token, secret_key=grow_secret_key)
    
    print("Initializing DataPipelineService...")
    pipeline = DataPipelineService(db=db, grow_extractor=extractor)
    await pipeline.initialize()
    
    print("Pipeline status:")
    status = pipeline.get_status()
    print(status)
    
    print("\nRunning extraction for symbol 'RELIANCE'...")
    job = await pipeline.run_extraction(symbols=["RELIANCE"], extraction_type="quotes")
    
    print("\nJob completed:")
    print(job.to_dict() if hasattr(job, "to_dict") else job)

if __name__ == "__main__":
    asyncio.run(main())
