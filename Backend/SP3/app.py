from shiny import App, render, ui
from sklearn.cluster import KMeans
from shinyswatch import theme
import numpy as np
import pandas as pd
import os
from selenium import webdriver
from shinywidgets import output_widget, render_widget
import plotly.express as px
import plotly.graph_objs as go
from htmltools import HTMLDependency
import geopandas as gpd
from shapely import Point
import json 
from pathlib import Path
from bs4 import BeautifulSoup

current_directory = os.getcwd()
data_directory = os.path.join(current_directory, 'data')
isochrone_directory = os.path.join(current_directory, 'data\Isochrone_data')
file_path1 = os.path.join(isochrone_directory, 'mrt_station_colours.csv')
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
bus_isochrones = pd.read_json(os.path.join(isochrone_directory, 'bus_isochrones.json'), orient='records', lines=True)
bicycle_isochrones = pd.read_json(os.path.join(isochrone_directory, 'bicycle_isochrones.json'), orient='records', lines=True)
mrt_isochrones = pd.read_json(os.path.join(isochrone_directory, 'mrt_isochrones.json'), orient='records', lines=True)
public_transport_isochrones = pd.read_json(os.path.join(isochrone_directory, 'public_isochrones.json'), orient='records', lines=True)
mrt_names = mrt_df['MRT.Name'].values.tolist()
coords = mrt_df[['Latitude', 'Longitude']].values.tolist()
basemap = gpd.read_file(os.path.join(data_directory, 'MasterPlan2019PlanningAreaBoundaryNoSea.geojson'))
mrt_stations_df = pd.read_csv(os.path.join(data_directory, 'Cluster_data','mrt_station_final.csv'),usecols = [1,2,3])
ranking = pd.read_csv(os.path.join(data_directory,'Cluster_data','mrt_ranking.csv'))

app_ui = ui.page_navbar(
    theme.minty(),
    ui.nav_panel("Sub-Problem 1: Cycling infrastructure suitability index","a"),
    ui.nav_panel("Sub-Problem 2: Last Mile Acessibility Index",
                 ui.h2("Rankings by Planning Area"),
                 ui.input_select("metrics", "Select Metric for Comparison", 
                                 choices=["Suitability", "Time Savings", "Weighted Score"],
                                 selected = "Suitability"),
                ui.layout_columns(
                    ui.card(
                        output_widget("chloropeth_map")
                    ),
                    ui.card(
                        ui.output_data_frame("path_metric")
                    )
                )
    ),
    ui.nav_panel("Sub-Problem 3: Isochrone Analysis",
                ui.h2("Distance Travellable from MRT/LRT Stations"),
                ui.page_sidebar(
                ui.sidebar(ui.input_selectize(
                    "transport_means",
                    "Select the means of movement",
                    ["Bus", "Bicycle", "MRT", "Public_Transport"],
                    multiple=True
                ),ui.input_selectize(
                    "station",
                    "Select the MRT/LRT station",
                    mrt_names,
                    multiple=True
                ),
                # Set step to 5 for intervals of 5 minutes
                ui.input_slider(
                    "n_min",
                    "Select Maximum Time (in minutes)",
                    min=10, max=60, value=5, step=5
                ), 
                bg="#f8f8f8"
                ),
                ui.output_text_verbatim("txt"),
                output_widget("plot")
                )
                ),
    title = "DSE3101 Cycle",
    bg= "#20c997"
    )

def server(input, output, session):
    #SP2 Functions
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

    
    basemap['Planning_Area'] = basemap["Description"].apply(lambda x:extract_td_contents(x)[0])
    basemap['geometry'] = basemap['geometry'].to_crs("4326")

    mrt_stations_df.sort_values(by='MRT.Name', inplace=True)
    
    mrt_stations_df_combined = pd.merge(mrt_stations_df, ranking, left_on='MRT.Name', right_on='MRT.Name', how='left')
    for index, row in mrt_stations_df_combined.iterrows():
        point_coordinate = Point(row['Longitude'], row['Latitude'])
        Planning_Area = basemap[basemap.geometry.contains(point_coordinate)]['Planning_Area'].reset_index(drop=True)
        mrt_stations_df_combined.loc[index, 'Planning_Area'] = Planning_Area.values[0]

    mrt_stations_df_combined = mrt_stations_df_combined.rename(columns = {'MRT.Name':'MRT Name',
                                                                        'time_difference':'Time Savings',
                                                                        'Weighted_Score':'Weighted Score',
                                                                        'suitability':'Suitability'})
    
    path_metrics = pd.read_csv(os.path.join(data_directory, 'path_metrics.csv'))
    path_metrics = path_metrics.astype(str)

    @output 
    @render_widget
    def chloropeth_map():
        df = mrt_stations_df_combined.groupby('Planning_Area').agg({input.metrics():'mean'}).reset_index()
        basemap_modified = pd.merge(basemap, df, left_on='Planning_Area', right_on='Planning_Area', how='left')
        fig = go.Figure()
        fig.add_trace(go.Choroplethmapbox(geojson=json.loads(basemap_modified.geometry.to_json()), 
                                   locations=basemap_modified.index,
                                   z=basemap_modified[input.metrics()],
                                   colorscale='RdYlGn',
                                   hoverinfo = 'text',
                                   text = ("Planning Area: " + basemap_modified['Planning_Area'] + '<br>' + 
                                           "Average " + input.metrics() + " of Paths Within the Area: " + round(basemap_modified[input.metrics()],2).astype(str) )))
        
        fig.add_trace(go.Scattergeo(geojson=json.loads(basemap_modified.geometry.to_json()),
                                    locations = basemap_modified.index,
                                    featureidkey= 'properties.index',
                                    text = basemap_modified['Planning_Area'],
                                    mode = 'text',))

        fig.update_layout(
            margin={'l':0,'t':0,'b':0,'r':0},
            mapbox={
                'style': "open-street-map",
                'center': {'lat': 1.36, 'lon': 103.85},
                'zoom': 10
            }
        )
        return fig
    
    @output
    @render.data_frame
    def path_metric():
        return render.DataTable(path_metrics,width = "100%",height = "300px")

    
    #SP3
    def get_isochrone(name, mode, cutoff):
        variable_name = f"{mode}_isochrones"    
        df = globals()[variable_name] 
        filtered_df = df[(df['MRT.Name'] == name)]
        isochrone = filtered_df[f'isochrone_{cutoff}M'].iloc[0]
        return isochrone

    @render.text
    def txt():
        # Generate the initial text string
        initial_text = f"You are trying to find the maximum distance that can be travelled within {input.n_min()} minutes by {input.transport_means()} from the following stations:"
        
        # Initialize an empty list to store the lines
        lines = [initial_text]
        
        # Iterate over each station in the tuple
        for station in input.station():
            lines.append(f"• {station.strip()}")
    
        # Join the lines with newline characters
        return '\n'.join(lines)
    @render_widget
    def plot():
        fig = go.Figure()
        
        for _, row in mrt_df.iterrows():
            fig.add_trace(go.Scattermapbox(
                mode="markers",
                lon=[row['Longitude']],
                lat=[row['Latitude']],
                text=[row['MRT.Name']],
                name=row['MRT.Name'],
                marker=dict(size=6, color='grey'),  # Use a neutral color for all stations
                textposition="bottom center",
                hoverinfo='text'
            ))

        # Fetch and add isochrones for each selected MRT station
        for mrt_name in input.station():
            for transport_means in input.transport_means():
                transport_means = transport_means.lower()
                # Extracting color and coordinates for the current MRT station
                station_row = mrt_df[mrt_df['MRT.Name'] == mrt_name].iloc[0]
                color = station_row["Color"]
                lat, lon = station_row['Latitude'], station_row['Longitude']
                
                # Convert cutoff to minutes, e.g. "15M" to 15
                cutoff = int(input.n_min())
                
                # Fetch the isochrone data
                isochrone = get_isochrone(name=mrt_name, mode=transport_means, cutoff=cutoff)
                lon_coords = [coord[0] for coord in isochrone]
                lat_coords = [coord[1] for coord in isochrone]
                    
                # Add isochrone as a trace
                fig.add_trace(go.Scattermapbox(
                    mode="lines",
                    lon=lon_coords,
                    lat=lat_coords,
                    name=f"Isochrone {lat}, {lon}",
                    line=dict(width=1, color=color),
                    fill="toself",
                    hoverinfo = "none"
                ))
                # Add MRT station as a marker
                fig.add_trace(go.Scattermapbox(
                    mode="markers",
                    lon=[lon],
                    lat=[lat],
                    text=[mrt_name],
                    name=mrt_name,
                    marker=dict(size=10, color=color),
                    textposition="bottom center",
                    hoverinfo='text'
                ))

        # Update the layout to match the provided example
        fig.update_layout(
            mapbox_style="carto-positron",
            mapbox_zoom=12,
            mapbox_center={"lat": coords[0][0], "lon": coords[0][1]},
            showlegend=False,
            width=1300,
            height=600
        )

        # Show the figure
        return fig
            

app = App(app_ui, server)
if __name__ == "__main__":
    app.run()