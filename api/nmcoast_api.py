'''
Program:        NM COAST 2025 API
Author:         Brendan Kearns
Last Updated:   05-30-2025
Purpose:        Download data from vendors into a centralized database.
                Serve 15-minute and daily counts to NM COAST front-end.
'''

### Module Imports ###
from pydantic import BaseModel
from pydantic import Field
from enum import Enum
from typing import Optional
from typing import List
from datetime import datetime
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import status
import uvicorn
import random
from datetime import timedelta

from fastapi.middleware.cors import CORSMiddleware

### Global Variables ###

### Eco-Visio Data Download Module ###

class EcoVisioDownload:
    '''
    Download data from Eco-Counter, process it, and save it to database.
    '''
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
                "latitude": 34.052235,
                "longitude": -118.243683,
                "counter_notes": "",
            }
        }

class DatastreamType(str, Enum):
    '''
    Defines the possible types of a datastream.
    '''
    PEDESTRIAN = "Pedestrian"
    ROADWAY_CYCLIST = "Roadway Cyclist"
    SIDEWALK_CYCLIST = "Sidewalk Cyclist"
    COMBINED = "Combined"

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
                "datastream_type": "Pedestrian",
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
                "datastream_id": "DS-ABC-001",
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


# Mock data - Charlotte, NC focused

mock_counters = [
    Counter(
        counter_id=1,
        counter_code="BOA_STADIUM",
        counter_name="Bank of America Stadium",
        vendor="SensorCorp",
        latitude=35.225833,
        longitude=-80.852778,
        counter_notes="Main entrance"
    ),
    Counter(
        counter_id=2,
        counter_code="BOA_SOUTH",
        counter_name="Stadium South Gate",
        vendor="SensorCorp",
        latitude=35.226,
        longitude=-80.853,
        counter_notes="South gate entrance"
    ),
    Counter(
        counter_id=3,
        counter_code="FREEDOM_PARK",
        counter_name="Freedom Park Main Entrance",
        vendor="TrailTech",
        latitude=35.186,
        longitude=-80.827,
        counter_notes="Park main entrance"
    ),
    Counter(
        counter_id=4,
        counter_code="SUGAR_CREEK",
        counter_name="Little Sugar Creek Greenway",
        vendor="TrailTech",
        latitude=35.198,
        longitude=-80.840,
        counter_notes="Trailhead counter"
    ),
    Counter(
        counter_id=5,
        counter_code="ROMARE_BEARDEN",
        counter_name="Romare Bearden Park",
        vendor="TrailTech",
        latitude=35.225,
        longitude=-80.844,
        counter_notes="Downtown park entrance"
    ),
    Counter(
        counter_id=6,
        counter_code="CONVENTION",
        counter_name="Charlotte Convention Center",
        vendor="SensorCorp",
        latitude=35.223,
        longitude=-80.841,
        counter_notes="Main lobby entrance"
    ),
    Counter(
        counter_id=7,
        counter_code="MINT_MUSEUM",
        counter_name="Mint Museum",
        vendor="SensorCorp",
        latitude=35.224,
        longitude=-80.839,
        counter_notes="Front entrance"
    ),
    Counter(
        counter_id=8,
        counter_code="FIRST_WARD",
        counter_name="First Ward Park",
        vendor="TrailTech",
        latitude=35.232,
        longitude=-80.836,
        counter_notes="North entrance"
    ),
    Counter(
        counter_id=9,
        counter_code="FOURTH_WARD",
        counter_name="Fourth Ward Park",
        vendor="TrailTech",
        latitude=35.235,
        longitude=-80.840,
        counter_notes="Main gate"
    ),
    Counter(
        counter_id=10,
        counter_code="LIGHT_RAIL",
        counter_name="Lynx Light Rail Station",
        vendor="SensorCorp",
        latitude=35.221,
        longitude=-80.838,
        counter_notes="Platform entrance"
    ),
]

mock_datastreams = [
    # Bank of America Stadium
    Datastream(
        datastream_id=1,
        counter_id=1,
        datastream_type=DatastreamType.PEDESTRIAN,
        datastream_name="Main Gate Pedestrians In",
        datastream_direction=DatastreamDirection.IN
    ),
    Datastream(
        datastream_id=2,
        counter_id=1,
        datastream_type=DatastreamType.PEDESTRIAN,
        datastream_name="Main Gate Pedestrians Out",
        datastream_direction=DatastreamDirection.OUT
    ),
    # Stadium South Gate
    Datastream(
        datastream_id=3,
        counter_id=2,
        datastream_type=DatastreamType.PEDESTRIAN,
        datastream_name="South Gate Pedestrians In",
        datastream_direction=DatastreamDirection.IN
    ),
    # Freedom Park
    Datastream(
        datastream_id=4,
        counter_id=3,
        datastream_type=DatastreamType.COMBINED,
        datastream_name="Park Entrance Combined",
        datastream_direction=DatastreamDirection.COMBINED
    ),
    Datastream(
        datastream_id=5,
        counter_id=3,
        datastream_type=DatastreamType.ROADWAY_CYCLIST,
        datastream_name="Cyclist Road Entrance",
        datastream_direction=DatastreamDirection.IN
    ),
    # Little Sugar Creek
    Datastream(
        datastream_id=6,
        counter_id=4,
        datastream_type=DatastreamType.SIDEWALK_CYCLIST,
        datastream_name="Trailhead Cyclists",
        datastream_direction=DatastreamDirection.NORTHBOUND
    ),
    # Romare Bearden Park
    Datastream(
        datastream_id=7,
        counter_id=5,
        datastream_type=DatastreamType.PEDESTRIAN,
        datastream_name="Main Park Entrance In",
        datastream_direction=DatastreamDirection.IN
    ),
    Datastream(
        datastream_id=8,
        counter_id=5,
        datastream_type=DatastreamType.PEDESTRIAN,
        datastream_name="Main Park Entrance Out",
        datastream_direction=DatastreamDirection.OUT
    ),
    # Convention Center
    Datastream(
        datastream_id=9,
        counter_id=6,
        datastream_type=DatastreamType.PEDESTRIAN,
        datastream_name="Main Lobby Entrance In",
        datastream_direction=DatastreamDirection.IN
    ),
    # Mint Museum
    Datastream(
        datastream_id=10,
        counter_id=7,
        datastream_type=DatastreamType.PEDESTRIAN,
        datastream_name="Front Entrance Combined",
        datastream_direction=DatastreamDirection.COMBINED
    ),
    # First Ward Park
    Datastream(
        datastream_id=11,
        counter_id=8,
        datastream_type=DatastreamType.PEDESTRIAN,
        datastream_name="North Entrance In",
        datastream_direction=DatastreamDirection.IN
    ),
    # Fourth Ward Park
    Datastream(
        datastream_id=12,
        counter_id=9,
        datastream_type=DatastreamType.PEDESTRIAN,
        datastream_name="Main Gate Combined",
        datastream_direction=DatastreamDirection.COMBINED
    ),
    # Light Rail Station
    Datastream(
        datastream_id=13,
        counter_id=10,
        datastream_type=DatastreamType.PEDESTRIAN,
        datastream_name="Platform Entrance In",
        datastream_direction=DatastreamDirection.IN
    ),
    Datastream(
        datastream_id=14,
        counter_id=10,
        datastream_type=DatastreamType.PEDESTRIAN,
        datastream_name="Platform Entrance Out",
        datastream_direction=DatastreamDirection.OUT
    ),
]

# Generate mock counts for all datastreams (May 27 - June 5, 2024)
mock_counts = []
count_id = 100
random.seed(42)  # For consistent results

start_date = datetime(2024, 5, 27)
end_date = datetime(2024, 6, 5)
times = [8, 12, 16, 20]  # 4 times per day

current_date = start_date
while current_date <= end_date:
    for datastream in mock_datastreams:
        for hour in times:
            # Generate random counts with realistic patterns
            base_count = random.randint(30, 100)
            
            # Adjust counts based on time of day
            if hour == 8:  # Morning rush
                base_count = int(base_count * 1.8)
            elif hour == 12:  # Lunch time
                base_count = int(base_count * 1.5)
            elif hour == 16:  # Afternoon
                base_count = int(base_count * 1.3)
            elif hour == 20:  # Evening
                base_count = int(base_count * 1.2)
            
            # Weekend adjustments
            if current_date.weekday() >= 5:  # Saturday/Sunday
                base_count = int(base_count * 1.5)
                
            # Event days have higher counts
            if current_date.day in [27, 30, 3, 5]:  # Simulate event days
                base_count = int(base_count * 2.0)
                
            # Add some random variation
            raw_count = base_count + random.randint(-15, 15)
            if raw_count < 0:
                raw_count = 0
                
            # Generate cleaned count (slightly adjusted)
            cleaned_count = round(raw_count * random.uniform(0.95, 1.05), 1)
            
            # Generate QA flags (mostly pass, occasional failures)
            flags = {
                'maxday': 1,
                'maxhour': 1,
                'gap': 1,
                'zero': 1,
                'stat': 1
            }
            
            # 15% chance of a flag failure
            if random.random() < 0.15:
                failed_flag = random.choice(list(flags.keys()))
                flags[failed_flag] = 0
                
            # Create datetime object
            dt = datetime(
                current_date.year, 
                current_date.month, 
                current_date.day, 
                hour, 0, 0
            )
            
            mock_counts.append(Count(
                count_id=count_id,
                datastream_id=datastream.datastream_id,
                date_time=dt,
                raw_count=raw_count,
                cleaned_count=cleaned_count,
                maxday=flags['maxday'],
                maxhour=flags['maxhour'],
                gap=flags['gap'],
                zero=flags['zero'],
                stat=flags['stat']
            ))
            count_id += 1
    
    # Move to next day
    current_date += timedelta(days=1)


# FastAPI application
app = FastAPI(
    title="Mock Count Data API",
    description="A minimal API for frontend development with mock Counter, Datastream, and Count data.",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Counter endpoints

@app.get("/counters/", response_model=List[Counter], summary="Get all counters")
async def get_all_counters():
    '''
    Retrieve a list of all available counters.
    '''
    return mock_counters

@app.get("/counters/{counter_id}/datastreams/", response_model=List[Datastream], summary="Get datastreams for a specific counter")
async def get_datastreams_for_counter(counter_id: int):
    '''
    Retrieve a list of all datastreams associated with a given counter_id.
    Returns an empty list if the counter_id exists but has no datastreams,
    or raises a 404 if the counter_id itself is not found.
    '''
    # Check if counter_id exists
    counter_exists = any(counter.counter_id == counter_id for counter in mock_counters)
    if not counter_exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Counter with ID {counter_id} not found.")

    # Filter datastreams where the counter_id matches the one from the path
    associated_datastreams = [
        datastream for datastream in mock_datastreams
        if datastream.counter_id == counter_id
    ]
    return associated_datastreams

@app.get("/datastreams/{datastream_id}/counts", response_model=List[Count], summary="Get counts for a specific datastream")
async def get_counts_for_datastream(datastream_id: int):
    '''
    Retrieve a list of all count records associated with a given datastream_id.
    Returns an empty list if the datastream_id exists but has no counts,
    or raises a 404 if the datastream_id itself is not found.
    '''
    # Check if the datastream_id exists
    datastream_exists = any(ds.datastream_id == datastream_id for ds in mock_datastreams)
    if not datastream_exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Datastream with ID {datastream_id} not found.")

    # Filter counts where the datastream_id matches the one from the path
    associated_counts = [
        count for count in mock_counts
        if count.datastream_id == datastream_id
    ]
    return associated_counts

### Run app ###

if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8000)