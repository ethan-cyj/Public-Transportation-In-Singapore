import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import pandas as pd
import os

# Load your MRT data
current_directory = os.getcwd()
data_directory = os.path.join(current_directory, '../../data/Isochrone_data')
file_path1 = os.path.join(data_directory, 'mrt_station_colours.csv')
mrt_df = pd.read_csv(file_path1)
new_color_map = {
    'red': '#cb2721',
    'yellow': '#e69c3d',
    'green': '#159048',
    'blue': '#0b569d',
    'purple': '#7d4687',
    'brown': '#a67440',
    'grey': '#7c8981',
}
mrt_df['Color'] = mrt_df['Color'].map(new_color_map)

# Define the isochrones data frames
# Ensure these JSON files exist and contain the correct data structure
bus_isochrones = pd.read_json(os.path.join(data_directory, 'bus_isochrones.json'), orient='records', lines=True)
bicycle_isochrones = pd.read_json(os.path.join(data_directory, 'bicycle_isochrones.json'), orient='records', lines=True)
mrt_isochrones = pd.read_json(os.path.join(data_directory, 'mrt_isochrones.json'), orient='records', lines=True)
public_transport_isochrones = pd.read_json(os.path.join(data_directory, 'public_isochrones.json'), orient='records', lines=True)

def get_isochrone(name, mode, cutoff):
    variable_name = f"{mode}_isochrones"    
    df = globals()[variable_name] 
    filtered_df = df[(df['MRT.Name'] == name)]
    isochrone = filtered_df[f'isochrone_{cutoff}M'].iloc[0]
    return isochrone

# Define the app
app = dash.Dash(__name__)

# App layout
app.layout = html.Div([
    dcc.Graph(
        id='mrt-map',
        clickData=None,  # Reset click data
        config={"staticPlot": False, "scrollZoom": True, "doubleClick": "reset"}
    ),
    html.Div(id='selected-stations', style={'display': 'none'}),  # Hidden div to store selected stations
    dcc.Dropdown(
        id='transport-mode-dropdown',
        options=[
            {'label': 'Bus', 'value': 'bus'},
            {'label': 'Bicycle', 'value': 'bicycle'},
            {'label': 'MRT', 'value': 'mrt'},
            {'label': 'Public Transport', 'value': 'public_transport'}
        ],
        value='bus'  # Default value
    ),
    dcc.Slider(
        id='time-slider',
        min=10, max=60, step=5, value=15,
        marks={str(n): str(n) for n in range(10, 61, 5)}
    )
])

# Callback for updating the map
@app.callback(
    Output('mrt-map', 'figure'),
    [Input('mrt-map', 'clickData'),
     Input('time-slider', 'value'),
     Input('transport-mode-dropdown', 'value')],
    [State('selected-stations', 'children')]
)
def update_map(selected_stations, selected_time, selected_mode):
    fig = go.Figure()

    # Add all MRT stations as markers on the map
    for _, row in mrt_df.iterrows():
        fig.add_trace(go.Scattermapbox(
            mode='markers',
            lat=[row['Latitude']],
            lon=[row['Longitude']],
            marker=go.scattermapbox.Marker(
                size=9,
                color=row['Color'],
                opacity=0.5
            ),
            hoverinfo='text',
            hovertext=row['MRT.Name'],
            showlegend=False
        ))

    # Add selected isochrones to the map
    for station in selected_stations:
        isochrone = get_isochrone(station, selected_mode, selected_time)
        if isochrone:
            # Assuming the isochrone data contains 'coordinates' key
            lon = [coord[0] for coord in isochrone]
            lat = [coord[1] for coord in isochrone]
            color = mrt_df[mrt_df['MRT.Name'] == station]['Color'].iloc[0]
            fig.add_trace(go.Scattermapbox(
                mode='lines',
                lat=lat,
                lon=lon,
                fill='toself',
                fillcolor=color,
                hoverinfo='none',
                showlegend=False
            ))

    # Update the layout of the map
    fig.update_layout(
        mapbox=dict(
            style='open-street-map',
            zoom=11,
            center=dict(lat=mrt_df['Latitude'].mean(), lon=mrt_df['Longitude'].mean())
        ),
        margin={'l': 0, 't': 0, 'b': 0, 'r': 0}
    )
    
    return fig

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)
