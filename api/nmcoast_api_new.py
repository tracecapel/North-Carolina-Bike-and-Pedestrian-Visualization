'''
Program:        NM COAST 2025 API
Author:         Brendan Kearns
Last Updated:   06-20-2025
Purpose:        Download data from vendors into a centralized database.
                Serve 15-minute and daily counts to NM COAST front-end.
'''

### Module Imports ###

import pandas as pd
import numpy as np
from pydantic import BaseModel
from pydantic import Field
from pydantic import ValidationError
from enum import Enum
from typing import Optional
from typing import List
from typing import Union
from typing import get_origin
from typing import get_args
from datetime import datetime
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import status
from fastapi import APIRouter
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import os
import uvicorn

print('Modules successfully loaded.')

### Vendor Data Manipulation ###

class EcoVisioDownload:
    pass

### NM COAST API ###

# Pydantic models

class Counter(BaseModel):
    '''
    Pydantic model representing counting locations.
    '''
    counter_id: int
    counter_code: str
    counter_name: str
    vendor: str
    vendor_site_id : str
    latitude: float
    longitude: float
    counter_notes: Optional[str] = Field(None, description="Any additional notes or comments about this counter.")

    class Config:
        extra = "forbid" 
        json_schema_extra = {
            "example": {
                "counter_id": 12,
                "counter_code": "MAIN_ENTRANCE",
                "counter_name": "Main Building Entrance Counter",
                "vendor": "Acme Solutions Inc.",
                "vendor_site_id" : '24001',
                "latitude": 34.052235,
                "longitude": -118.243683,
                "counter_notes": "",
            }
        }

class DatastreamType(str, Enum):
    '''
    Defines the possible types of a datastream.
    '''
    PEDESTRIAN = "PEDESTRIAN"
    CYCLIST = "CYCLIST"
    ROADWAY_CYCLIST = "ROADWAY_CYCLIST"
    SIDEWALK_CYCLIST = "SIDEWALK_CYCLIST"
    COMBINED = "COMBINED"

class DatastreamDirection(str, Enum):
    '''
    Defines the possible directions for a datastream.
    '''
    IN = "IN"
    OUT = "OUT"
    NORTHBOUND = "NB"
    SOUTHBOUND = "SB"
    EASTBOUND = "EB"
    WESTBOUND = "WB"
    COMBINED = "COMBINED"

class Datastream(BaseModel):
    '''
    Pydantic model representing a data stream from a counter.
    '''
    datastream_id: int
    counter_id: int = Field(..., description="Foreign key linking to the Counter's counter_id.")
    datastream_type: DatastreamType = Field(..., description="The type of traffic being counted (e.g., Pedestrian, Cyclist).")
    datastream_name: str
    datastream_direction: DatastreamDirection = Field(..., description="The direction of the traffic flow for this datastream.")
    datastream_notes: Optional[str] = Field(None, description="Any additional notes or comments about the datastream.")
    class Config:
        extra = "forbid"
        json_schema_extra = {
            "example": {
                "datastream_id": 45,
                "counter_id": 13, 
                "datastream_type": "PEDESTRIAN",
                "datastream_name": "Main Entrance Pedestrian Count",
                "datastream_direction": "IN",
                "datastream_notes": "",
            }
        }

class Count(BaseModel):
    """
    Pydantic model representing a single traffic or pedestrian count record.
    """
    count_id: int
    datastream_id: int = Field(..., description="Foreign key linking to the Datastream's datastream_id.")
    date_time: datetime
    raw_count: Optional[int] = Field(None, description="The raw, unadjusted count value from the sensor.")
    maxday: Optional[int] = Field(None, description="1 if this day of data passes the maximum daily volume non-statistical check, 0 if it fails")
    maxhour: Optional[int] = Field(None, description="1 if this day of data passes the maximum hourly volume non-statistical check, 0 if it fails")
    gap: Optional[int] = Field(None, description="1 if this day of data passes the missing data non-statistical check, 0 if it fails")
    zero: Optional[int] = Field(None, description="1 if this day of data passes the consecutive zero volumes non-statistical check, 0 if it fails")
    stat: Optional[int] = Field(None, description="1 if this day of data passes the statistical QAQC model check, 0 if it fails")
    cleaned_count: Optional[float] = Field(None, description="The adjusted or cleaned count value after processing.")

    class Config:
        extra = "forbid" # Forbid extra fields not defined in the model
        json_schema_extra = {
            "example": {
                "count_id": 101,
                "datastream_id": 45,
                "date_time": "2024-03-15T08:00:00+00:00",
                "raw_count": 150,
                "maxday": 0,
                "maxhour": 0,
                "gap": 0,
                "zero": 0,
                "stat": 1,
                "cleaned_count": None,
            }
        }

# SQL Manipulation

def validate_data(df: pd.DataFrame, model: BaseModel, file_path: str, chunk_info: Optional[str] = None) -> pd.DataFrame:
    """
    Validates a DataFrame chunk against a Pydantic model and returns a DataFrame of validated records.
    """
    TARGET_LOCAL_TZ = 'America/New_York'

    model_fields = model.model_fields
    validated_records = []
    errors = []

    df.columns = [col.lower().replace(' ', '_') for col in df.columns]

    for field_name, field_info in model_fields.items():
        if field_name not in df.columns:
            df[field_name] = None
            continue

        is_optional = get_origin(field_info.annotation) is Union and type(None) in get_args(field_info.annotation)
        base_type = next((arg for arg in get_args(field_info.annotation) if arg is not type(None)), field_info.annotation)

        if issubclass(base_type, str):
            df[field_name] = df[field_name].astype(str)
            if is_optional:
                df[field_name] = df[field_name].replace({'nan': None, '': None, 'None': None, pd.NA: None, np.nan: None})
            else:
                df[field_name] = df[field_name].fillna('')

        elif issubclass(base_type, (int, float)):
            if is_optional:
                df[field_name] = df[field_name].replace([np.nan, pd.NaT, float('inf'), float('-inf')], None)
                if issubclass(base_type, int):
                    df[field_name] = df[field_name].astype('Int64', errors='ignore')
                else: # float
                    df[field_name] = df[field_name].astype(float, errors='ignore')
            else: # Required int or float
                df[field_name] = df[field_name].replace([float('inf'), float('-inf')], np.nan) 
                df[field_name] = df[field_name].astype(base_type, errors='ignore') 

        elif issubclass(base_type, datetime):
            # *** CRITICAL CHANGE HERE: Parse to UTC first to ensure consistent dtype ***
            # This directly addresses the FutureWarning and the `.dt` accessor error.
            temp_dt_series = pd.to_datetime(df[field_name], format='ISO8601', utc=True, errors='coerce')
            
            # Identify valid parsed datetimes (not NaT)
            valid_dt_indices = temp_dt_series.notnull()

            # Process valid datetimes for timezone conversion to TARGET_LOCAL_TZ
            if not temp_dt_series[valid_dt_indices].empty:
                try:
                    # Now that temp_dt_series is guaranteed to be datetime64[ns, UTC],
                    # .dt.tz_convert can be reliably called to convert to the local timezone.
                    df.loc[valid_dt_indices, field_name] = temp_dt_series[valid_dt_indices].dt.tz_convert(TARGET_LOCAL_TZ)
                except Exception as e:
                    # This fallback should ideally not be hit as often now,
                    # but it's good for robustness against unexpected data.
                    print(f"Warning: dt.tz_convert to {TARGET_LOCAL_TZ} failed for some datetimes in chunk {chunk_info}: {e}. Problematic values might remain NaT or incorrect TZ.")
                    # If this still fails, let the values be NaT, which will become None and cause Pydantic to error.
            
            # Replace any remaining NaT (from original parse failures or conversion issues) with None.
            df[field_name] = df[field_name].replace({pd.NaT: None})
            
    df_to_validate = df[list(model_fields.keys())] 
    for idx, record_dict in enumerate(df_to_validate.to_dict(orient='records')):
        try:
            validated_record = model.model_validate(record_dict) 
            validated_records.append(validated_record.model_dump()) 
        except ValidationError as e:
            error_msg = f"Row {df.index[idx] + 2} (original index {df.index[idx]}) failed validation: {e.errors()}"
            errors.append(error_msg)
        except Exception as e:
            error_msg = f"Row {df.index[idx] + 2} (original index {df.index[idx]}) encountered an unexpected error: {e}"
            errors.append(error_msg)

    if errors:
        location_info = f" for {file_path}{' (' + chunk_info + ')' if chunk_info else ''}"
        print(f"--- Validation Errors{location_info} ---")
        for error in errors:
            print(error)
        print(f"----------------------------------------\n")
        raise ValueError(f"Data validation failed for some rows{location_info}. See logs above.")

    return pd.DataFrame(validated_records)


def load_data(file_path: str, model: BaseModel, table_name: str, engine) -> None:
    """
    Loads data from a CSV or XLSX file, validates it (in chunks for CSVs),
    and directly inserts the validated records into the specified SQL table.
    """
    print(f"\nLoading data from {file_path} into table '{table_name}'...")
    
    if engine is None:
        raise ValueError("Database engine must be provided for data loading.")

    _, file_extension = os.path.splitext(file_path)
    file_extension = file_extension.lower()

    if file_extension not in ('.csv', '.xlsx', '.xls'):
        raise ValueError(f"Unsupported file type for {file_path}. Must be .csv, .xlsx, or .xls.")

    total_validated_records = 0

    if file_extension == '.csv':
        chunk_size = 100000 # Adjust chunk size based on available memory
        csv_iterator = pd.read_csv(file_path, chunksize=chunk_size)
        
        for i, chunk_df in enumerate(csv_iterator):
            print(f"  Processing chunk {i+1}...")
            chunk_df.columns = [col.lower().replace(' ', '_') for col in chunk_df.columns]

            validated_chunk_df = validate_data(chunk_df, model, file_path, chunk_info=f"Chunk {i+1}")

            if not validated_chunk_df.empty:
                try:
                    # 'replace' for the first chunk to create/overwrite, 'append' for subsequent chunks
                    if i == 0:
                        validated_chunk_df.to_sql(table_name, engine, if_exists='replace', index=False)
                    else:
                        validated_chunk_df.to_sql(table_name, engine, if_exists='append', index=False)
                    total_validated_records += len(validated_chunk_df)
                    print(f"  Successfully loaded {len(validated_chunk_df)} records from chunk {i+1} into database.")
                except SQLAlchemyError as e:
                    print(f"Error inserting chunk {i+1} into database: {e}")
                    raise
    else: # .xlsx or .xls
        try:
            df = pd.read_excel(file_path)
            df.columns = [col.lower().replace(' ', '_') for col in df.columns]

            validated_df = validate_data(df, model, file_path)
            
            if not validated_df.empty:
                validated_df.to_sql(table_name, engine, if_exists='replace', index=False)
                total_validated_records = len(validated_df)
                print(f"Successfully loaded all {total_validated_records} valid records from {file_path} into database.")
            else:
                print(f"No valid records found in {file_path}.")

        except FileNotFoundError:
            print(f"Error: {file_path} not found. Please ensure the file exists.")
            return
        except Exception as e:
            print(f"An error occurred while loading {file_path}: {e}")
            raise

    print(f"Finished loading data from {file_path}. Total records inserted: {total_validated_records}.")


def create_initial_sql_database(db_name):
    """
    Create SQL database from existing counter, datastream, and count records.
    """
    database_url = f"sqlite:///{db_name}" # SQLite database file
    engine = create_engine(database_url)

   

    # Call load_data for each file, which now handles validation and direct insertion
    load_data('counters.xlsx', Counter, 'counters', engine)
    load_data('datastreams.xlsx', Datastream, 'datastreams', engine)
    load_data('counts.csv', Count, 'counts', engine)

    # Verify data in the database
    print("\n--- Verifying data in the database ---")
    with engine.connect() as connection:
        try:
            print("\nCounters table:")
            print(pd.read_sql("SELECT * FROM counters", connection))

            print("\nDatastreams table:")
            print(pd.read_sql("SELECT * FROM datastreams", connection))

            print("\nCounts table (first 5 rows):")
            print(pd.read_sql("SELECT * FROM counts LIMIT 5", connection))
        except Exception as e:
            print(f"Error verifying data: {e}")

    print(f"\nDatabase operations complete. Data loaded into '{database_url}'.")

class DatabaseManager:

    def __init__(self, db_name: str):
        self.database_url = f"sqlite:///{db_name}"
        self.engine = create_engine(self.database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def get_all_counters_from_db(self) -> List[Counter]:
        with self.engine.connect() as connection:
            try:
                df = pd.read_sql("SELECT * FROM counters", connection)
                return [Counter(**row) for row in df.to_dict(orient='records')]
            except SQLAlchemyError as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {e}")

    def get_datastreams_for_counter_from_db(self, counter_id: int) -> List[Datastream]:
        with self.engine.connect() as connection:
            try:
                df = pd.read_sql(f"SELECT * FROM datastreams WHERE counter_id = {counter_id}", connection)
                return [Datastream(**row) for row in df.to_dict(orient='records')]
            except SQLAlchemyError as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {e}")

    def get_counts_for_datastream_from_db(self, datastream_id: int) -> List[Count]:
        with self.engine.connect() as connection:
            try:
                df = pd.read_sql(f"SELECT * FROM counts WHERE datastream_id = {datastream_id}", connection)
                
                # Convert datetime columns
                df['date_time'] = pd.to_datetime(df['date_time'], errors='coerce')
                # If date_time is NOT Optional[datetime] and has NaT, Pydantic will error.
                # If it IS optional, uncomment: df['date_time'] = df['date_time'].replace({pd.NaT: None})

                # List of all optional numeric columns in the Count model
                optional_numeric_cols = [
                    'raw_count', 'maxday', 'maxhour', 'gap', 'zero', 'stat', 'cleaned_count'
                ]

                # Convert to Python dicts first
                records = df.to_dict(orient='records')

                # NOW, iterate through the list of dictionaries and explicitly clean values
                cleaned_records = []
                for record in records:
                    cleaned_record = record.copy() # Work on a copy
                    for col in optional_numeric_cols:
                        if col in cleaned_record:
                            value = cleaned_record[col]
                            
                            # Check for NaN from numpy
                            if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
                                cleaned_record[col] = None
                            # Check for string "nan" or "None"
                            elif isinstance(value, str) and value.lower() in ('nan', 'none', ''):
                                cleaned_record[col] = None
                            # If it's a numeric type that should be an int but isn't None
                            elif col in ['raw_count', 'maxday', 'maxhour', 'gap', 'zero', 'stat'] and value is not None:
                                try:
                                    cleaned_record[col] = int(value)
                                except (ValueError, TypeError):
                                    # If it can't be converted to int, force to None
                                    cleaned_record[col] = None
                            
                    cleaned_records.append(cleaned_record)
                
                # Debugging the cleaned records (optional)
                # if cleaned_records:
                #     print(f"\n--- DEBUG FINAL CLEANED RECORD SAMPLE ---")
                #     print(cleaned_records[0])
                #     if 'raw_count' in cleaned_records[0]:
                #         print(f"Type of raw_count in sample: {type(cleaned_records[0]['raw_count'])}")
                #         print(f"Value of raw_count in sample: {cleaned_records[0]['raw_count']}")
                # print(f"-------------------------------------------")

                return [Count(**row) for row in cleaned_records]

            except SQLAlchemyError as e:
                print(f"Database error in get_counts_for_datastream_from_db: {e}")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {e}")
            except Exception as e:
                print(f"An unexpected error occurred in get_counts_for_datastream_from_db: {e}")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {e}")


# Counter endpoints
class NMCOAST_API:
    def __init__(self, db_name: str = "traffic_data.db"):
        self.router = APIRouter(
            prefix="",  # You can add a common prefix for all routes in this class, e.g., "/api/v1"
            tags=["NM COAST"], # Tags for grouping endpoints in OpenAPI docs
            responses={404: {"description": "Not found"}},
        )
        self.db_manager = DatabaseManager(db_name) # Initialize db_manager
        self.register_routes() # Call the method to register routes

    def register_routes(self):
        @self.router.get("/counters/", response_model=List[Counter], summary="Get all counters")
        async def get_all_counters():
            '''
            Retrieve a list of all available counters.
            '''
            return self.db_manager.get_all_counters_from_db()

        @self.router.get("/counters/{counter_id}/datastreams/", response_model=List[Datastream], summary="Get datastreams for a specific counter")
        async def get_datastreams_for_counter(counter_id: int):
            '''
            Retrieve datastreams associated with a specific counter ID.
            '''
            datastreams = self.db_manager.get_datastreams_for_counter_from_db(counter_id)
            if not datastreams:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Datastreams not found for this counter.")
            return datastreams

        @self.router.get("/datastreams/{datastream_id}/counts", response_model=List[Count], summary="Get counts for a specific datastream")
        async def get_counts_for_datastream(datastream_id: int):
            '''
            Retrieve counts for a specific datastream ID.
            '''
            counts = self.db_manager.get_counts_for_datastream_from_db(datastream_id)
            if not counts:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Counts not found for this datastream.")
            return counts


# Create FastAPI app
app = FastAPI(
    title="NM COAST Test API", 
    version="0.1.0",
    description="API for North Carolina bike and pedestrian counting data"
)

# Configure CORS 
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://127.0.0.1:3000",
        "http://localhost:8080", 
        "http://127.0.0.1:8080",
        "http://localhost:5000",  
        "http://127.0.0.1:5000",
        "file://",  
        "*"  # Allow all origins - REMOVE in production!
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Add a simple health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "NM COAST API is running"}

### Execute on Application Start ###
if __name__ == '__main__':
    
    # create_initial_sql_database("traffic_data.db")
    
    
    api_instance = NMCOAST_API("api/traffic_data.db")
    app.include_router(api_instance.router)
    
    
    print("Starting NM COAST API server...")
    print("API will be available at: http://localhost:8000")
    print("API documentation will be available at: http://localhost:8000/docs")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info"
    )