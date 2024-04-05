import geopandas as gpd
from shapely import Point
import numpy as np
import pandas as pd
import os
from bs4 import BeautifulSoup
import json
import yaml

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

    cluster_ranking['lg_time_difference'] = cluster_ranking['time_difference'].apply(np.log)

    cluster_ranking = cluster_ranking.rename(columns = {'MRT.Name':'MRT Name',
                                                        'time_difference':'Time Savings',
                                                        'lg_time_difference':'Time Savings(Log)',
                                                        'Weighted_Score':'Weighted Score',
                                                        'suitability':'Suitability',
                                                        'distance':'Distance'})
    return basemap,cluster_ranking

def SP2_Prep_Centroid_MRT_Metrics():
    hdb_centroid_pair_df = pd.read_csv(os.path.join(data_directory, 'Cluster_data','HDB_Centroid_MRT pairing data.csv'))
    private_centroid_pair_df = pd.read_csv(os.path.join(data_directory, 'Cluster_data','Private_Centroid_MRT pairing data.csv'))
    hdb_centroid_pair_df = hdb_centroid_pair_df.drop(hdb_centroid_pair_df.columns[:2], axis=1)
    private_centroid_pair_df = private_centroid_pair_df.drop(private_centroid_pair_df.columns[:3], axis=1)
    combined_df = pd.concat([hdb_centroid_pair_df, private_centroid_pair_df], axis=0).reset_index(drop=True)
    combined_df['steepness'] = abs(combined_df['steepness'])
    combined_df['time_difference'] = -combined_df['time_difference'] #Reflect time savings as a positive number
    combined_df['cycle_route'] = combined_df['cycle_route'].apply(lambda x: yaml.load(x, Loader=yaml.SafeLoader))
    output = combined_df[combined_df.columns[[0,1,16,5,6,4,12,13,14,15,17,18,10]]].copy(deep = True)

    basemap = gpd.read_file(os.path.join(data_directory, 'MasterPlan2019PlanningAreaBoundaryNoSea.geojson'))
    basemap['Planning_Area'] = basemap["Description"].apply(lambda x:extract_td_contents(x)[0])
    basemap['geometry'] = basemap['geometry'].to_crs("4326")

    for index,row in output.iterrows():
        point_coordinate = Point(row['Longitude_x'], row['Latitude_x'])
        Planning_Area = basemap[basemap.geometry.contains(point_coordinate)]['Planning_Area'].reset_index(drop=True)
        output.loc[index, 'Planning_Area'] = Planning_Area.values[0]

    return output

# def calculate_weighted_score(dataframe,row1,row2,row3,row4):
#     S = row1 * dataframe["distance"] + row2 * dataframe['suitability'] + row3 * dataframe["time_difference"] + row4 * dataframe["steepness"]
#     return S

def calculate_weighted_score(dataframe, row1, row2, row3, row4):
    numeric_columns = dataframe.select_dtypes(include='number')
    standardized_numeric_columns = (numeric_columns - numeric_columns.mean()) / numeric_columns.std()
    S = row1 * standardized_numeric_columns["distance"] + row2 * standardized_numeric_columns['suitability'] + row3 * standardized_numeric_columns["time_difference"] + row4 * standardized_numeric_columns["steepness"]
    
    # Normalize S to a 0-100 range
    S_normalized = (S - S.min()) / (S.max() - S.min()) * 100
    
    return S_normalized
