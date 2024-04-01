import plotly.graph_objects as go
import numpy as np
import os
import json
import shapely
import geopandas as gpd
import pandas as pd
import csv
import fiona
fiona.drvsupport.supported_drivers['KML'] = 'rw'


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

    hazards = gpd.read_file(file_path6, driver='KML')
    hazards['Lon'] = hazards.geometry.apply(lambda p: p.x)
    hazards['Lat'] = hazards.geometry.apply(lambda p: p.y)

    return subZoneScore, parkConnector_lats, parkConnector_lons, bicycleParking, cyclingPath_lats, cyclingPath_lons, hazards


def createMap(subZoneScore, parkConnector_lats, parkConnector_lons, bicycleParking, cyclingPath_lats, cyclingPath_lons, hazards): #edf, vdf, edfColMap, vdfColMap, eSizeCol = 'Magnitude', vSizeCol = 'Population Within 100km'):
    '''
    Function to create the map
    '''
    fig = go.FigureWidget(
        data = [
            go.Choroplethmapbox(
                geojson=json.loads(subZoneScore.geometry.to_json()),
                locations=subZoneScore.index,
                colorscale="mint",
                z=subZoneScore['score'],
                text = subZoneScore['DESCRIPTION'],
                hovertemplate="%{text}<br><br><span style = \"font-size: 1.2em;\"><b>Overall Score: </b>: %{z}</span>"
                ),
            go.Scattermapbox(
                lat=parkConnector_lats,
                lon=parkConnector_lons,
                mode='lines',
                marker=go.scattermapbox.Marker(
                    size=3,
                    opacity=0.7
                ),
                name = 'Park Connector',
                legendgroup = 'Lines'
            ),                
            go.Scattermapbox(
                lat=list(bicycleParking["Lat"]),
                lon=list(bicycleParking['Lon']),
                mode='markers',
                marker=go.scattermapbox.Marker(
                    size=3,
                    opacity=0.7
                )
                ,text= bicycleParking["Description"]+ "</br>" + "Number of Racks: " + bicycleParking["RackCount"],
                name = 'Bicycle Parking',
                legendgroup = 'Lines'
            ),
            go.Scattermapbox(
                lat=cyclingPath_lats,
                lon=cyclingPath_lons,
                mode='lines',
                marker=go.scattermapbox.Marker(
                    size=3,
                    opacity=0.7
                ),
                name = 'Cycling Paths',
                legendgroup = 'Lines'
            ), 
            go.Scattermapbox(
                lat=list(hazards["Lat"]),
                lon=list(hazards['Lon']),
                mode='markers',
                marker=go.scattermapbox.Marker(
                    size=3,
                    opacity=0.7
                )
                ,text= hazards["Name"]+ "</br>",
                name = 'Hazards',
                legendgroup = 'Lines'
            )                        
        ]
    )

    fig.update_layout(
        margin ={'l':0,'t':0,'b':0,'r':0},
        mapbox = {
            'style': "open-street-map",
            'center': {'lon': 104, 'lat': 1.39},
            'zoom': 10},
        legend=dict(yanchor = 'top',
                    y = 0.99,
                    x=0.99,
                    xanchor = 'right')
                    )


    return fig