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

# def get_filter_areas():
#     region = {}
#     return result

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
                colorscale=['rgba(50, 108, 110, 0.5)', 'rgba(32, 88, 95, 1.0)'],
                z=subZoneScore['score'],
                text = subZoneScore['DESCRIPTION'],
                hovertemplate="%{text}<br><br><span style = \"font-size: 1.2em;\"><b>Overall Score: </b>: %{z}</span>"
                ),
            go.Scattermapbox(
                lat=parkConnector_lats,
                lon=parkConnector_lons,
                mode='lines',
                hovertemplate="Park Connector",
                name = 'Park Connector',
                legendgroup = 'Lines'
            ), 
            go.Scattermapbox(
                lat=cyclingPath_lats,
                lon=cyclingPath_lons,
                mode='lines',
                hovertemplate="Cycling Path",
                name = 'Cycling Paths',
                legendgroup = 'Lines'
            ),                
            go.Scattermapbox(
                lat=list(bicycleParking["Lat"]),
                lon=list(bicycleParking['Lon']),
                mode='markers',
                marker=go.scattermapbox.Marker(
                    size=3,
                    opacity=0.7
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