from pymongo import AsyncMongoClient
import dotenv
import os
import logging
from beanie import Document, Indexed, init_beanie
import app.schemas

dotenv.load_dotenv()

class DBMongo:
    client = AsyncMongoClient = None
    
db = DBMongo()

async def connect_to_mongo():
    logger = logging.getLogger(__name__)
    mongo_uri = os.getenv("MONGODB_DATABASE")
    if not mongo_uri:
        logger.error("MONGODB_DATABASE environment variable not set")
        return False

    try:
        db.client = AsyncMongoClient(mongo_uri)
        
        document_models = [
            model for model in app.schemas.__dict__.values()
            if isinstance(model, type) and issubclass(model, Document)
        ]
        
        if os.getenv("MONGODB_CLUSTER") is None:
            logger.error("MONGODB_CLUSTER environment variable not set")
            return False

        await init_beanie(database=db.client[os.getenv("MONGODB_CLUSTER")], document_models=document_models)
        
        # If the client exposes an async connect hook, await it
        if hasattr(db.client, "aconnect"):
            await db.client.aconnect()
        else:
            # Try a lightweight ping to verify the connection if possible
            try:
                admin_cmd = getattr(db.client, "admin", None)
                if admin_cmd is not None and hasattr(admin_cmd, "command"):
                    cmd = admin_cmd.command("ping")
                    if hasattr(cmd, "__await__"):
                        await cmd
            except Exception:
                # If ping fails, we'll treat it as a connection error below
                raise

    except Exception as e:
        logger.exception("Failed to connect to MongoDB: %s", e)
        db.client = None
        return False

    logger.info("Successfully connected to MongoDB")
    return True
    
    
async def close_mongo_connection():
    if db.client is not None:
        await db.client.close()