from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from .config import settings

DATABASE_URL = f"postgresql+asyncpg://{settings.database_username}:{settings.database_password}@{settings.database_hostname}:{settings.database_port}/{settings.database_name}"
engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session



# from sqlalchemy import create_engine
# from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.orm import sessionmaker
# from.config import settings

# SQLALCHEMY_DATABASE_URL = f"postgresql://{settings.database_username}:{settings.database_password}@{settings.database_hostname}:{settings.database_port}/{settings.database_name}"
# engine = create_engine(SQLALCHEMY_DATABASE_URL)
# AsyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Base = declarative_base()

# def get_db():
#     db = AsyncSessionLocal()
#     try:
#         yield db
#     finally:
#         db.close() 





# # Connection to the PostgreSQL database
# #try:
#     #conn = psycopg.connect(
#         #host='localhost',
#         #dbname='FASTAPI',
#         #user='postgres',
#         #password='1123111231Lm.',
#         #row_factory=dict_row
#     #)
#     #cursor = conn.cursor()
#     #print("Database connection was successful!")
# #except Exception as error:
#     #print("Connecting to database failed")
#     #print("Error:", error)
#     #raise  
