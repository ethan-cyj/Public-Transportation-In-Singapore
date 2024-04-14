#This file reads the MRT stations from a shapefile and extracts the latitude and longitude of each MRT station using the OneMap API. 
#File is checked for the MRT stations that were not found in the API response.
#The extracted data is then saved to a CSV file.

from dbfread import DBF
from http.client import HTTPConnection
import json
import pandas as pd
import geopandas as gpd
import requests
df = gpd.read_file("../data/MRT/RapidTransitSystemStation.shp")
mrt_list = df['STN_NAM_DE']

#Extracting the MRT stations
part1_url = "https://www.onemap.gov.sg/api/common/elastic/search?searchVal="
part2_url = "&returnGeom=Y&getAddrDetails=Y&pageNum=1"

# Initialize an empty list to store the data
data_list = []

# Iterate through each MRT name in the list
for mrt_name in mrt_list:
    url = part1_url + mrt_name + part2_url
    response = requests.get(url)
    data = json.loads(response.text)
    
    # Check if results exist
    if 'results' in data and len(data['results']) > 0:
        # Extracting the first search result
        first_result = data['results'][0]
        # Getting the latitude and longitude
        latitude = first_result['LATITUDE']
        longitude = first_result['LONGITUDE']
        # Append MRT name, latitude, and longitude to the data list
        data_list.append({'MRT Name': mrt_name, 'Latitude': latitude, 'Longitude': longitude})

# Create a DataFrame from the data list
df = pd.DataFrame(data_list)

# Print the DataFrame
print(df)

mrt_names_in_df = set(df['MRT Name'])

# Convert the list of MRT names to a set
mrt_names_list = set(mrt_list)

# Find the MRT names that are in the list but not in the DataFrame
mrt_names_not_in_df = mrt_names_list - mrt_names_in_df

# Print the MRT names not in the DataFrame
print("MRT names not in DataFrame:")
for mrt_name in mrt_names_not_in_df:
    print(mrt_name)

df.to_csv("../data/MRT/mrt_stations.csv")