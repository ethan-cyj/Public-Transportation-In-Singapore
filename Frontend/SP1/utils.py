import plotly.graph_objects as go


def prepData():
    ''' 
    Function to read in and prep the data
    '''
    current_directory = os.getcwd()
    data_directory = os.path.join(current_directory, 'data') #../../
    file_path1 = os.path.join(data_directory, 'subZoneScore.csv')
    file_path2 = os.path.join(data_directory, 'ParkConnectorLoop.geojson')


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

    #ParkConnectorLoop map #parkConnector = gpd.read_file(r"..\data\ParkConnectorLoop.geojson")
    vdf = pd.read_csv('data/volcano.csv')
    vdf['Population Within 100km'] = np.nan_to_num((vdf['population_within_100_km'] - np.amin(vdf['population_within_100_km']))/(np.amax(vdf['population_within_100_km']) - np.amin(vdf['population_within_100_km']))*50., 0)
    vdf['Elevation (m)'] = np.nan_to_num(((vdf['elevation'] - np.amin(vdf['elevation']))/(np.amax(vdf['elevation']) - np.amin(vdf['elevation'])))*20., 0)
    # a map between the normalized and regular columns so that I can plot histograms
    vdfColMap = {'Population Within 100km':'population_within_100_km', 'Elevation (m)':'elevation'}

    return edf, vdf #, edfColMap, vdfColMap


def createMap(edf, vdf, edfColMap, vdfColMap, eSizeCol = 'Magnitude', vSizeCol = 'Population Within 100km'):
    '''
    Function to create the map
    '''

    fig = go.FigureWidget(
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
    )

    return fig