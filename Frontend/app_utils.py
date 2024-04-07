import geopandas as gpd
from shapely import Point
import shapely
import numpy as np
import pandas as pd
import geopandas as gpd
import os
from bs4 import BeautifulSoup
import json
import yaml
from pyonemap import OneMap
from dotenv import load_dotenv
import requests
import plotly.graph_objects as go
import csv
import fiona
fiona.drvsupport.supported_drivers['KML'] = 'rw' #setting up KML reader

current_directory = os.getcwd()
data_directory = os.path.join(current_directory, 'data')

#SP1

def get_filter_areas():
    region = ['CENTRAL REGION','EAST REGION', 'NORTH REGION', 'NORTH-EAST REGION','WEST REGION']
    planning_area_central = ['BISHAN', 'BUKIT MERAH', 'BUKIT TIMAH', 'DOWNTOWN CORE', 'GEYLANG', 'KALLANG', 'MARINA EAST', 'MARINA SOUTH',
        'MARINE PARADE', 'MUSEUM', 'NEWTON', 'NOVENA', 'ORCHARD', 'OUTRAM', 'QUEENSTOWN', 'RIVER VALLEY', 'ROCHOR', 'SINGAPORE RIVER',
        'SOUTHERN ISLANDS', 'STRAITS VIEW', 'TANGLIN', 'TOA PAYOH']
    planning_area_east = ['BEDOK', 'CHANGI', 'CHANGI BAY', 'PASIR RIS', 'PAYA LEBAR', 'TAMPINES']
    planning_area_north = ['CENTRAL WATER CATCHMENT','LIM CHU KANG', 'MANDAI', 'SEMBAWANG', 'SIMPANG', 'SUNGEI KADUT', 'WOODLANDS', 'YISHUN']
    planning_area_north_east = ['ANG MO KIO', 'HOUGANG', 'NORTH-EASTERN ISLANDS', 'PUNGGOL', 'SELETAR', 'SENGKANG', 'SERANGOON']
    planning_area_west = ['BOON LAY', 'BUKIT BATOK', 'BUKIT PANJANG', 'CHOA CHU KANG', 'CLEMENTI', 'JURONG EAST', 'JURONG WEST',
        'PIONEER', 'TENGAH', 'TUAS', 'WESTERN ISLANDS', 'WESTERN WATER CATCHMENT']
    
    planning_area = ['ANG MO KIO','BEDOK', 'BISHAN', 'BOON LAY', 'BUKIT BATOK', 'BUKIT MERAH',
            'BUKIT PANJANG', 'BUKIT TIMAH', 'CENTRAL WATER CATCHMENT', 'CHANGI', 'CHANGI BAY', 'CHOA CHU KANG',
            'CLEMENTI', 'DOWNTOWN CORE', 'GEYLANG', 'HOUGANG', 'JURONG EAST', 'JURONG WEST', 'KALLANG', 'LIM CHU KANG', 
            'MANDAI', 'MARINA EAST', 'MARINA SOUTH', 'MARINE PARADE', 'MUSEUM',
            'NEWTON', 'NORTH-EASTERN ISLANDS', 'NOVENA', 'ORCHARD', 'OUTRAM', 'PASIR RIS', 
            'PAYA LEBAR', 'PIONEER', 'PUNGGOL', 'QUEENSTOWN', 'RIVER VALLEY', 'ROCHOR', 'SELETAR', 'SEMBAWANG', 'SENGKANG',
            'SERANGOON', 'SIMPANG', 'SINGAPORE RIVER', 'SOUTHERN ISLANDS', 'STRAITS VIEW', 'SUNGEI KADUT', 'TAMPINES', 
            'TANGLIN', 'TENGAH', 'TOA PAYOH', 'TUAS', 'WESTERN ISLANDS', 'WESTERN WATER CATCHMENT','WOODLANDS', 'YISHUN']
    return region,planning_area, planning_area_central, planning_area_east, planning_area_north, planning_area_north_east, planning_area_west

def get_zoom(poly):
    poly_mapped = shapely.geometry.mapping(poly)
    poly_coordinates = poly_mapped['coordinates'][0]
    poly_ = [{'lat': coords[1],'lon': coords[0]} for coords in poly_coordinates]
    latlons = poly_[:-1]
    lats = []
    lons = []
    for i in latlons:
        lats.append(i['lat'])
        lons.append(i['lon'])

    maxlon, minlon = max(lons), min(lons)
    maxlat, minlat = max(lats), min(lats)
    center = {
        'lon': round((maxlon + minlon) / 2, 6),
        'lat': round((maxlat + minlat) / 2, 6)
    }
    lon_zoom_range = np.array([
    0.0007, 0.0014, 0.003, 0.006, 0.012, 0.024, 0.048, 0.096,
    0.192, 0.3712, 0.768, 1.536, 3.072, 6.144, 11.8784, 23.7568,
    47.5136, 98.304, 190.0544, 360.0])
    margin = 1.2
    width_to_height=1
    adjustment = 0.5
    height = (maxlat - minlat) * margin * width_to_height
    width = (maxlon - minlon) * margin
    lon_zoom = np.interp(width , lon_zoom_range, range(20, 0, -1))
    lat_zoom = np.interp(height, lon_zoom_range, range(20, 0, -1))
    zoom = round(min(lon_zoom, lat_zoom), 2) - adjustment
    return zoom

def city_centers(subZoneScore):
    result = {}
    for index, row in subZoneScore.iterrows():
        name = row['SUBZONE_N']
        center = row['geometry'].centroid
        lon,lat = center.xy
        result[name] = {'lon':lon[0], 'lat':lat[0]}
    return result


def prepData():
    ''' 
    Function to read in and prep the data
    '''
    current_directory = os.getcwd()
    data_directory = os.path.join(current_directory, 'data') #../../
    file_path1 = os.path.join(data_directory, 'subZoneScore.csv')
    file_path2 = os.path.join(data_directory, 'ParkConnectorLoop.geojson')
    file_path3 = os.path.join(data_directory, 'unique_bicycle_parking_data.csv')
    file_path4 = os.path.join(data_directory, 'MasterPlan2019RegionBoundaryNoSeaGEOJSON.geojson')
    file_path5 = os.path.join(data_directory, 'CyclingPath_Jul2023\CyclingPathGazette.shp')
    file_path6 = os.path.join(data_directory, 'Choke Points.kml')

    #Index Map
    subZoneScore = pd.read_csv(file_path1)
    subZoneScore['geometry'] = subZoneScore['geometry'].apply(shapely.from_wkt)
    subZoneScore = gpd.GeoDataFrame(subZoneScore)

    parkConnector = gpd.read_file(file_path2)
    parkConnector_lats = []
    parkConnector_lons = []
    for feature in parkConnector.geometry:
        if isinstance(feature, shapely.geometry.linestring.LineString):
            linestrings = [feature]
        elif isinstance(feature, shapely.geometry.multilinestring.MultiLineString):
            linestrings = feature.geoms
        else:
            continue
        for linestring in linestrings:
            x, y = linestring.xy
            parkConnector_lats = np.append(parkConnector_lats, y)
            parkConnector_lons = np.append(parkConnector_lons, x)
            parkConnector_lats = np.append(parkConnector_lats, None)
            parkConnector_lons = np.append(parkConnector_lons, None)

    basemap = gpd.read_file(file_path4)
    cyclingPath = gpd.read_file(file_path5)
    cyclingPath = cyclingPath.to_crs(basemap.crs)
    cyclingPath_lats = []
    cyclingPath_lons = []
    for feature in cyclingPath.geometry:
        if isinstance(feature, shapely.geometry.linestring.LineString):
            linestrings = [feature]
        elif isinstance(feature, shapely.geometry.multilinestring.MultiLineString):
            linestrings = feature.geoms
        else:
            continue
        for linestring in linestrings:
            x, y = linestring.xy
            cyclingPath_lats = np.append(cyclingPath_lats, y)
            cyclingPath_lons = np.append(cyclingPath_lons, x)
            cyclingPath_lats = np.append(cyclingPath_lats, None)
            cyclingPath_lons = np.append(cyclingPath_lons, None)

    bicycleParkingTemp = []
    with open(file_path3, newline='') as csvfile:
        csv_reader = csv.reader(csvfile, delimiter=',', quotechar='"')
        for row in csv_reader:
            bicycleParkingTemp.append(row)
    bicycleParkingTemp = pd.DataFrame(bicycleParkingTemp)
    bicycleParking=bicycleParkingTemp.iloc[1:,:]
    bicycleParking = bicycleParking.rename(columns = {0:'Description',1:'Lat',2:'Lon',3:'RackType',4:'RackCount',5:'ShelterIndicator'})
    bicycleParking.reset_index()
    bicycleParking[["Lat", "Lon"]] = bicycleParking[["Lat", "Lon"]].apply(pd.to_numeric)

    chokePoints = gpd.read_file(file_path6, driver='KML')
    chokePoints['Lon'] = chokePoints.geometry.apply(lambda p: p.x)
    chokePoints['Lat'] = chokePoints.geometry.apply(lambda p: p.y)

    return subZoneScore, parkConnector_lats, parkConnector_lons, cyclingPath_lats, cyclingPath_lons, bicycleParking, chokePoints


def createMap(subZoneScore, parkConnector_lats, parkConnector_lons, cyclingPath_lats, cyclingPath_lons, bicycleParking, chokePoints):
    '''
    Function to create the map
    '''
    fig = go.FigureWidget(
        data = [
            go.Choroplethmapbox(
                geojson=json.loads(subZoneScore.geometry.to_json()),
                locations=subZoneScore.index,
                colorscale=['rgba(147, 220, 187, 0.65)', 'rgba(20, 156, 88, 1.0)'],
                z=subZoneScore['score'],
                text = subZoneScore['DESCRIPTION'],
                hovertemplate="%{text}<br>",
                colorbar={"title": 'Deeper color<br>has better<br>infrastructure'}
                ),
            go.Scattermapbox(
                lat=parkConnector_lats,
                lon=parkConnector_lons,
                mode='lines',
                fillcolor = 'red',
                hovertemplate="Park Connector",
                name = 'Park Connector',
                legendgroup = 'Lines'
            ), 
            go.Scattermapbox(
                lat=cyclingPath_lats,
                lon=cyclingPath_lons,
                mode='lines',
                fillcolor = 'red',
                hovertemplate="Cycling Path",
                name = 'Cycling Paths',
                legendgroup = 'Lines'
            ),                
            go.Scattermapbox(
                lat=list(bicycleParking["Lat"]),
                lon=list(bicycleParking['Lon']),
                mode='markers',
                marker=go.scattermapbox.Marker(
                    size=5,
                    opacity=0.5,
                    color = 'blue',
                ),
                text= bicycleParking["Description"],
                hovertext = bicycleParking["RackCount"],
                hovertemplate="<b>Name</b>: %{text}<br><b>Number of Racks</b>: %{hovertext}",
                name = 'Bicycle Parking',
                legendgroup = 'Lines'
            ),
            go.Scattermapbox(
                lat=list(chokePoints["Lat"]),
                lon=list(chokePoints['Lon']),
                mode='markers',
                fillcolor = 'purple',
                marker=go.scattermapbox.Marker(
                    size=5
                )
                ,text= chokePoints["Name"],
                hovertemplate="<b>Name</b>: %{text}<br><b>Lat</b>: %{lat} <b>Lon</b>: %{lon}",
                name = 'chokePoints',
                legendgroup = 'Lines'
            )                        
        ]
    )

    fig.update_layout(
        height = 500,
        margin ={'l':0,'t':0,'b':0,'r':0},
        mapbox = {
            'style': "open-street-map",
            'center': {'lon': 103.82904052734375, 'lat': 1.354625368768736},
            'zoom': 10},
        legend=dict(yanchor = 'top',
                    y = 0.99,
                    x=0.99,
                    xanchor = 'right')
                    )


    return fig



#SP2
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

    with open(os.path.join(data_directory, 'Cluster_data','indiv_combined_centroid_data_cycle_routes.json'),'r') as f:
        geojson_list_1 = json.load(f)

    indiv_combined_centroid_df['cycle_route'] = geojson_list_1
    indiv_combined_centroid_df['steepness'] = abs(indiv_combined_centroid_df['steepness'])
    indiv_combined_centroid_df['time_difference'] = -indiv_combined_centroid_df['time_difference'] #Reflect time savings as a positive number

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
        if location['found'] <=5:
            lat, long =0,0
            for i in range(location['found']):
                lat += float(location['results'][i]['LATITUDE'])
                long += float(location['results'][i]['LONGITUDE'])
            lat = lat/location['found']
            long = long/location['found']
        else:
            lat = float(location['results'][0]['LATITUDE'])
            long = float(location['results'][0]['LONGITUDE'])
    else:
        print("No locations found")
        return None
    print(lat,long)
    #find nearest centroid
    df['euclidean'] = df.apply(lambda x: haversine(lat, long, x['Latitude_x'], x['Longitude_x']), axis=1)
    df = df[df['euclidean'] == df['euclidean'].min()]
    return (df["Latitude_x"].values[0], df["Longitude_x"].values[0])