import plotly.graph_objects as go
import os
import json
import shapely
import geopandas as gpd
import pandas as pd
import csv


def prepData():
    ''' 
    Function to read in and prep the data
    '''
    current_directory = os.getcwd()
    data_directory = os.path.join(current_directory, 'data') #../../
    file_path1 = os.path.join(data_directory, 'subZoneScore.csv')
    file_path2 = os.path.join(data_directory, 'ParkConnectorLoop.geojson')
    file_path3 = os.path.join(data_directory, 'unique_bicycle_parking_data.csv')


    #Index Map
    subZoneScore = pd.read_csv(file_path1)
    subZoneScore['geometry'] = subZoneScore['geometry'].apply(shapely.from_wkt)
    subZoneScore = gpd.GeoDataFrame(subZoneScore)

    # edf = pd.read_csv('data/usgs_main.csv')
    # edf['time'] = pd.to_datetime(edf['time'])
    # powmag = 10.**edf['mag']
    # edf['Magnitude'] = np.nan_to_num((powmag - np.amin(powmag))/(np.amax(powmag) - np.amin(powmag))*100,0)
    # edf['Depth (km)'] = np.nan_to_num((edf['depth'] - np.amin(edf['depth']))/(np.amax(edf['depth']) - np.amin(edf['depth']))*20.,0)
    # # a map between the normalized and regular columns so that I can plot histograms
    # edfColMap = {'Magnitude':'mag', 'Depth (km)':'depth'}

    #ParkConnectorLoop map #with bicycleParking
    parkConnector = gpd.read_file(file_path2)

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



    # vdf = pd.read_csv('data/volcano.csv')
    # vdf['Population Within 100km'] = np.nan_to_num((vdf['population_within_100_km'] - np.amin(vdf['population_within_100_km']))/(np.amax(vdf['population_within_100_km']) - np.amin(vdf['population_within_100_km']))*50., 0)
    # vdf['Elevation (m)'] = np.nan_to_num(((vdf['elevation'] - np.amin(vdf['elevation']))/(np.amax(vdf['elevation']) - np.amin(vdf['elevation'])))*20., 0)
    # # a map between the normalized and regular columns so that I can plot histograms
    # vdfColMap = {'Population Within 100km':'population_within_100_km', 'Elevation (m)':'elevation'}

    return subZoneScore, parkConnector, bicycleParking #edf, vdf, edfColMap, vdfColMap


def createMap(subZoneScore, parkConnector, bicycleParking): #edf, vdf, edfColMap, vdfColMap, eSizeCol = 'Magnitude', vSizeCol = 'Population Within 100km'):
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
                lat=list(bicycleParking["Lat"]),
                lon=list(bicycleParking['Lon']),
                mode='markers',
                marker=go.scattermapbox.Marker(
                    size=3,
                    opacity=0.7
                )
                ,text= bicycleParking["Description"]+ "</br>" + "Number of Racks: " + bicycleParking["RackCount"]
            )
        ]
    )

    fig.update_layout(
        margin ={'l':0,'t':0,'b':0,'r':0},
        mapbox = {
            'center': {'lon': 103.9, 'lat': 1.38},
            'style': "open-street-map",
            'center': {'lon': 103.9, 'lat': 1.38},
            'zoom': 10})

    '''fig = go.FigureWidget(
        data = [
            go.Scattermapbox(
                lat = edf['latitude'],
                lon = edf['longitude'],
                mode = 'markers',
                marker = go.scattermapbox.Marker(
                    size = edf[eSizeCol].to_numpy(),
                    sizemin = 1.5,
                    sizemode = 'diameter',
                    color = '#0d6aff',
                    opacity = 0.5
                ),
                text = edf['place'] + '<br>' + eSizeCol +': ' + edf[edfColMap[eSizeCol]].astype('str')+ '<br>Date: ' + edf['time'].dt.strftime('%b %d, %Y'),
                hoverinfo = 'text'
            ),
            go.Scattermapbox(
                lat = vdf['latitude'],
                lon = vdf['longitude'],
                mode = 'markers',
                marker = go.scattermapbox.Marker(
                    size = vdf[vSizeCol].to_numpy(),
                    sizemin = 1.5,
                    sizemode = 'diameter',
                    color = '#ff1d0d',
                    opacity = 0.5
                ),
                text = vdf['volcano_name'] + '<br>' + vSizeCol +': ' + vdf[vdfColMap[vSizeCol]].astype('str') + '<br>Last Eruption Year: ' + vdf['last_eruption_year'].astype('str'),
                hoverinfo = 'text'
            )
        ],
        layout = dict(
            autosize = True,
            hovermode = 'closest',
            height = 500,
            width = 1000,
            margin = {"r":0,"t":0,"l":0,"b":0},
            mapbox = dict(
                style = 'carto-darkmatter',
                zoom = 0.9
            ),
            showlegend = False,
        )
    )'''

    return fig