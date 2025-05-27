from motor.motor_asyncio import AsyncIOMotorClient as _mongo_client_
from pymongo import MongoClient, server_api as pymongo_server_api # Added server_api for modern MongoDB
from pyrogram import Client

import config

# Assuming LOGGER is initialized in the parent package or a shared logging module
from ..logging import LOGGER
_log = LOGGER(__name__)

TEMP_MONGODB_URI_PLACEHOLDER = "mongodb://localhost:27017/clonify_temp_db" # A more descriptive placeholder

_mongo_async_ = None
_mongo_sync_ = None
mongodb = None # Async database object
pymongodb = None # Sync database object

if config.MONGO_DB_URI:
    _log.info(f"Attempting to connect to MongoDB using URI from config: {config.MONGO_DB_URI[:config.MONGO_DB_URI.find('@') if '@' in config.MONGO_DB_URI else 30]}...") # Log sanitized URI
    try:
        # For modern MongoDB Atlas, specify ServerApiVersion
        # Consider adding retry logic for initial connection if needed.
        _mongo_async_ = _mongo_client_(config.MONGO_DB_URI) # server_api=pymongo_server_api.ServerApi('1') can be added if using Atlas
        _mongo_sync_ = MongoClient(config.MONGO_DB_URI) # server_api=pymongo_server_api.ServerApi('1')

        # Attempt a basic operation to confirm connection (optional, but good for startup)
        # Example: _mongo_async_.admin.command('ping') 
        # This requires being awaited in an async context, so might be better in an async setup function.
        
        # Default database name, can be overridden by specific collection accessors
        # Using 'Anon' as per original, but consider making this configurable too.
        DB_NAME = "Anon" # Or config.MONGO_DB_NAME if you add it to config
        mongodb = _mongo_async_[DB_NAME]
        pymongodb = _mongo_sync_[DB_NAME]
        _log.info(f"Successfully connected to MongoDB and selected database '{DB_NAME}'.")
    except Exception as e:
        _log.critical(f"Failed to connect to MongoDB using provided URI. Error: {e}", exc_info=True)
        _log.critical("MongoDB connection is critical. Exiting application.")
        exit() # Or raise a specific exception to be handled by the main app startup
else:
    _log.warning("MONGO_DB_URI not found in config. Application will proceed without MongoDB.")
    _log.warning("Functionality requiring database persistence will be affected or disabled.")
    # The original code tries to use a temporary client and a TEMP_MONGODB URI which was empty.
    # This is highly problematic as it would try to connect to an empty string.
    # If MongoDB is optional, all DB operations throughout the code must handle mongodb/pymongodb being None.
    # For now, explicitly setting them to None if no URI.
    # If a fallback local/temp DB was intended, TEMP_MONGODB_URI_PLACEHOLDER should be a valid default URI.
    
    # If you want a fallback temporary DB (e.g., for testing or limited local use):
    # _log.info(f"Using fallback temporary MongoDB URI: {TEMP_MONGODB_URI_PLACEHOLDER}")
    # try:
    #     _mongo_async_ = _mongo_client_(TEMP_MONGODB_URI_PLACEHOLDER)
    #     _mongo_sync_ = MongoClient(TEMP_MONGODB_URI_PLACEHOLDER)
    #     # Determine a temporary DB name, perhaps based on bot username if Pyrogram client is available
    #     # This part was problematic in original as temp_client was not properly awaited for get_me
    #     # and was used to name a DB. Better to use a fixed temp name or make it configurable.
    #     TEMP_DB_NAME = "clonify_temp_default" 
    #     mongodb = _mongo_async_[TEMP_DB_NAME]
    #     pymongodb = _mongo_sync_[TEMP_DB_NAME]
    #     _log.info(f"Connected to fallback temporary MongoDB. DB Name: {TEMP_DB_NAME}")
    # except Exception as e_temp:
    #     _log.error(f"Failed to connect to fallback temporary MongoDB. Error: {e_temp}", exc_info=True)
    #     _log.warning("MongoDB functionality will be unavailable.")
    #     mongodb = None # Ensure it's None if fallback also fails
    #     pymongodb = None

# It's crucial that any code using `mongodb` or `pymongodb` checks if they are None
# before attempting database operations if MongoDB is optional. Example:
# if mongodb:
#     await mongodb.mycollection.insert_one(...)
# else:
#     _log.warning("MongoDB not available. Skipping DB operation.")
