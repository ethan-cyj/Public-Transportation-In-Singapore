from shiny import App, render, ui
from sklearn.cluster import KMeans
import numpy as np
import pandas as pd
import os
from selenium import webdriver
from shinywidgets import output_widget, render_widget
import plotly.express as px
import plotly.graph_objs as go
import requests

current_directory = os.getcwd()
files_in_directory = os.listdir(current_directory)
data_directory = os.path.join(current_directory, 'data')
file_path1 = os.path.join(data_directory, 'mrt_station_final.csv')
file_path2 = os.path.join(data_directory, 'mrt_station_colours.csv')
mrt_df = pd.read_csv(file_path1)
mrt_color = pd.read_csv(file_path2)
mrt_names = mrt_df['MRT.Name'].values.tolist()
coords = mrt_df[['Latitude', 'Longitude']].values.tolist()

app_ui = ui.page_fluid(
    ui.h2("Transport Medium"),
    ui.input_select("transport_means", "Select the means of movement", ["TRANSIT","Bus","Cycling","MRT+Bus","Bus+Cycling","MRT+Cycling"]),
    ui.input_selectize("station", "Select the MRT station", mrt_names,multiple=True),
    ui.input_slider("n_min", "Select Maximum Time (in minutes)", 0, 60, 5),
    ui.output_text_verbatim("txt"),
    output_widget("plot")
)

def server(input, output, session):
    def fetch_isochrone(lat, lon, modes, cutoff):
        """Fetch isochrone GeoJSON for a given location."""
        url = "http://localhost:8080/otp/traveltime/isochrone"
        params = {
            "batch": "true",
            "location": f"{lat},{lon}",
            "time": "2023-06-01T18:00:00+02:00",
            "modes": modes,
            "arriveBy": "false",
            "cutoff": cutoff
        }
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to fetch isochrone for {lat},{lon}. Status code: {response.status_code}")
            return None
    @render.text
    def txt():
        return f"You are trying to find the maximum distance that can be travelled by {input.transport_means()}\nfrom {input.station()}\nwithin {input.n_min()} minutes"
    
    @render_widget
    def plot():
        fig1 = go.Figure()
        minutes = '%02d' % (input.n_min())
        cutoff = minutes+"M00S"
        modes = input.transport_means()
        for mrt_name in input.station():
            lat = mrt_df[(mrt_df['MRT.Name'] == mrt_name)]['Latitude'].iloc[0]
            lon = mrt_df[(mrt_df['MRT.Name'] == mrt_name)]['Longitude'].iloc[0]
            color = mrt_color[mrt_color['MRT.Name'] == mrt_name]['Color'].iloc[0]
            station_isochrone = fetch_isochrone(lat,lon,modes,cutoff)
            if station_isochrone and 'features' in station_isochrone:
                # Access the first feature in the returned GeoJSON
                feature = station_isochrone['features'][0]
                if 'geometry' in feature:
                    geometry = feature['geometry']
                    if 'coordinates' in geometry:
                        coordinates = geometry['coordinates'][0][0]
                        # Assuming coordinates are in [lon, lat] format
                        lon_coords = [coord[0] for coord in coordinates]
                        lat_coords = [coord[1] for coord in coordinates]
                        fig1.add_trace(go.Scattermapbox(
                            mode="lines",
                            lon=lon_coords,
                            lat=lat_coords,
                            name=f"Isochrone {lat}, {lon}",
                            line=dict(width=1, color=color),
                            fill = "toself",
                            marker=dict(size=0),
                            text=[mrt_name],  # Set text for hover
                            hoverinfo='text'
                        ))
                        fig1.add_trace(go.Scattermapbox(
                            mode="markers",
                            lon=[lon],
                            lat=[lat],
                            text=[mrt_name],
                            name=mrt_name,
                            marker=dict(size=10,color=color),
                            textposition="bottom center",
                        ))
        # Define layout for the map
        fig1.update_layout(
            mapbox_style="carto-positron",
            mapbox_zoom=12,
            mapbox_center={"lat": coords[0][0], "lon": coords[0][1]},
            showlegend = False
        )
        return fig1.show()
            

app = App(app_ui, server)