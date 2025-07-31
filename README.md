**Overview**


This project is a demonstration tool to visualize and gain deeper insights into recorded pedestrian and bike activity all throughout North Carolina. Counters placed throughout the state at key locations measure bike and pedestrian traffic and log this data into a centralized database with millions of entries. The goal of this project is to be able to interact and visualize this data in an intuitive and user friendly way.

<img width="1869" height="947" alt="image" src="https://github.com/user-attachments/assets/f559b44d-a5bd-45c8-91a8-ac0446760184" />

The map displays counter locations. You can search for counters via name or ID or search manually on the map. Clicking the "download counters metadata" button will download metadata of all of the current counters on the map. This incudes things such as the latitude, longitude, name, ID etc for each counter. 

<img width="1869" height="947" alt="image" src="https://github.com/user-attachments/assets/9983c7e6-7b10-4602-8c21-153d60703e4b" />
When you click a counter, you also have the additional option of downloading all the selected counters datastreams and counts. This is all of the raw data collected by the counter, and includes consolidated counts as well as seperate datastreams.

<img width="1869" height="947" alt="image" src="https://github.com/user-attachments/assets/725bb16e-d41b-4002-96d7-119d6fa17e7d" />


Double clicking a counter will re-direct you to an Apache Superset dashboard displaying insights into activity. It is split by bike/pedestrian datastreams. It shows activity from the past month, total recorded counts all time, monthly total counts for the previous calendar year, average counts by hour of the day, and most popular days of the week. Note that a "count" is a record of activity, ie. if one person walks past a counter that is a "count".


**Requirements**

# Python Packages
fastapi
uvicorn
pandas
numpy
python-dotenv
sqlalchemy
pydantic

# Django packages
djangorestframework
django-cors-headers 
django-mapbox-location-field



# Other 
Mapbox Access Token (Free)
Apache Superset  


Additional Notes: 

CORS headers is configured to allow all origins as some browsers block superset/mapbox/API but this should be changed in production. 

The dashboard is currently only locally hosted. In order to configure your own dashboard, I reccomend taking a look at this article: https://www.blef.fr/superset-filters-in-url/. This will explain how to pass URL paramaters and filter the dashboard based on a selected counter.


