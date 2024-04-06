import geopandas as gpd
from shapely import Point
import numpy as np
import pandas as pd
import os
from bs4 import BeautifulSoup
import json
import yaml
from pyonemap import OneMap
from dotenv import load_dotenv
import requests

current_directory = os.getcwd()
data_directory = os.path.join(current_directory, 'data')

def extract_td_contents(html):
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table')
    rows = table.find_all('tr')

    td_contents = []
    for row in rows:
        cells = row.find_all('td')
        for cell in cells:
            td_contents.append(cell.text.strip())

    return td_contents

def SP2_prep_Chloropeth_Map():
    basemap = gpd.read_file(os.path.join(data_directory, 'MasterPlan2019PlanningAreaBoundaryNoSea.geojson'))
    mrt_stations_df = pd.read_csv(os.path.join(data_directory, 'Cluster_data','mrt_station_final.csv'),usecols = [1,2,3])
    cluster_ranking = pd.read_csv(os.path.join(data_directory,'Cluster_data','5_cluster_mrt_ranking.csv'))
        
    basemap['Planning_Area'] = basemap["Description"].apply(lambda x:extract_td_contents(x)[0])
    basemap['geometry'] = basemap['geometry'].to_crs("4326")

    mrt_stations_df.sort_values(by='MRT.Name', inplace=True)
        
    for index, row in cluster_ranking.iterrows():
        point_coordinate = Point(row['Longitude'], row['Latitude'])
        Planning_Area = basemap[basemap.geometry.contains(point_coordinate)]['Planning_Area'].reset_index(drop=True)
        cluster_ranking.loc[index, 'Planning_Area'] = Planning_Area.values[0]

    #cluster_ranking['lg_time_difference'] = cluster_ranking['time_difference'].apply(np.log)
    cluster_ranking['lg_time_difference'] = (cluster_ranking['time_difference'] + abs(cluster_ranking['time_difference'].min()) + 1).apply(np.log)

    cluster_ranking = cluster_ranking.rename(columns = {'MRT.Name':'MRT Name',
                                                        'time_difference':'Time Savings',
                                                        'lg_time_difference':'Time Savings(Log)',
                                                        'Weighted_Score':'Weighted Score',
                                                        'suitability':'Suitability',
                                                        'distance':'Distance'})
    return basemap,cluster_ranking

def SP2_Prep_Centroid_MRT_Metrics():
    indiv_combined_centroid_df = pd.read_csv(os.path.join(data_directory, 'Cluster_data','indiv_combined_centroid_data_fixed.csv'),index_col = 0)
    indiv_combined_centroid_df['steepness'] = abs(indiv_combined_centroid_df['steepness'])
    indiv_combined_centroid_df['time_difference'] = -indiv_combined_centroid_df['time_difference'] #Reflect time savings as a positive number

    for index,row in indiv_combined_centroid_df.iterrows():
        try:
            indiv_combined_centroid_df.at[index,'cycle_route'] = yaml.load(row['cycle_route'], Loader=yaml.FullLoader)
        except Exception as e:
            continue

    output = indiv_combined_centroid_df[indiv_combined_centroid_df.columns[[0,1,4,5,6,10,12,13,14,15,16,17,18,19]]].copy(deep = True)
    basemap = gpd.read_file(os.path.join(data_directory, 'MasterPlan2019PlanningAreaBoundaryNoSea.geojson'))
    basemap['Planning_Area'] = basemap["Description"].apply(lambda x:extract_td_contents(x)[0])
    basemap['geometry'] = basemap['geometry'].to_crs("4326")

    for index,row in output.iterrows():
        point_coordinate = Point(row['Longitude_x'], row['Latitude_x'])
        Planning_Area = basemap[basemap.geometry.contains(point_coordinate)]['Planning_Area'].reset_index(drop=True)
        output.loc[index, 'Planning_Area'] = Planning_Area.values[0]

    return output
    # hdb_centroid_pair_df = pd.read_csv(os.path.join(data_directory, 'Cluster_data','HDB_Centroid_MRT pairing data.csv'))
    # private_centroid_pair_df = pd.read_csv(os.path.join(data_directory, 'Cluster_data','Private_Centroid_MRT pairing data.csv'))
    # hdb_centroid_pair_df = hdb_centroid_pair_df.drop(hdb_centroid_pair_df.columns[:2], axis=1)
    # private_centroid_pair_df = private_centroid_pair_df.drop(private_centroid_pair_df.columns[:3], axis=1)
    # combined_df = pd.concat([hdb_centroid_pair_df, private_centroid_pair_df], axis=0).reset_index(drop=True)
    # combined_df['steepness'] = abs(combined_df['steepness'])
    # combined_df['time_difference'] = -combined_df['time_difference'] #Reflect time savings as a positive number
    # combined_df['cycle_route'] = combined_df['cycle_route'].apply(lambda x: yaml.load(x, Loader=yaml.SafeLoader))
    # output = combined_df[combined_df.columns[[0,1,16,5,6,4,12,13,14,15,17,18,10]]].copy(deep = True)

    # basemap = gpd.read_file(os.path.join(data_directory, 'MasterPlan2019PlanningAreaBoundaryNoSea.geojson'))
    # basemap['Planning_Area'] = basemap["Description"].apply(lambda x:extract_td_contents(x)[0])
    # basemap['geometry'] = basemap['geometry'].to_crs("4326")

    # for index,row in output.iterrows():
    #     point_coordinate = Point(row['Longitude_x'], row['Latitude_x'])
    #     Planning_Area = basemap[basemap.geometry.contains(point_coordinate)]['Planning_Area'].reset_index(drop=True)
    #     output.loc[index, 'Planning_Area'] = Planning_Area.values[0]

    # return output

# def calculate_weighted_score(dataframe,row1,row2,row3,row4):
#     S = row1 * dataframe["distance"] + row2 * dataframe['suitability'] + row3 * dataframe["time_difference"] + row4 * dataframe["steepness"]
#     return S

def calculate_weighted_score(dataframe, row1, row2, row3, row4):
    numeric_columns = dataframe.select_dtypes(include='number')
    standardized_numeric_columns = (numeric_columns - numeric_columns.mean()) / numeric_columns.std()
    S = row1 * -standardized_numeric_columns["distance"] + row2 * standardized_numeric_columns['suitability'] + row3 * standardized_numeric_columns["time_difference"] + row4 * -standardized_numeric_columns["steepness"]
    
    # Normalize S to a 0-100 range
    S_normalized = (S - S.min()) / (S.max() - S.min()) * 100
    
    return S_normalized

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # Earth radius in kilometers
    lat1 = np.radians(lat1)
    lon1 = np.radians(lon1)
    lat2 = np.radians(lat2)
    lon2 = np.radians(lon2)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    distance = R * c
    return distance


def SP2_get_centroid_from_postal_code(address):
    if address == None or address == "" or type(address) != str:
        return None
    load_dotenv()
    df = pd.read_csv(os.path.join(data_directory, 'Cluster_data','indiv_combined_centroid_data_fixed.csv'),index_col = 0)
    df = df[["centroid_name","Latitude_x","Longitude_x","MRT.Name"]]
    #search for average coords of api results
    one_map_email = os.getenv("ONE_MAP_EMAIL")
    one_map_password = os.getenv("ONE_MAP_PASSWORD")
    payload = {
            "email": one_map_email,
            "password": one_map_password
        }
    api_key = requests.request("POST", "https://www.onemap.gov.sg/api/auth/post/getToken", json=payload)
    api_key = api_key.json()["access_token"]
    onemap = OneMap(api_key)
    location = onemap.search(address)
    if location['found'] and location['found'] > 0:
        lat, long =0,0
        for i in range(location['found']):
            lat += float(location['results'][i]['LATITUDE'])
            long += float(location['results'][i]['LONGITUDE'])
        lat = lat/location['found']
        long = long/location['found']
    else:
        print("No locations found")
        return None
    print(lat,long)
    #find nearest centroid
    df['euclidean'] = df.apply(lambda x: haversine(lat, long, x['Latitude_x'], x['Longitude_x']), axis=1)
    df = df[df['euclidean'] == df['euclidean'].min()]
    return (df["Latitude_x"].values[0], df["Longitude_x"].values[0])