from shiny import App, render, ui
from sklearn.cluster import KMeans
import numpy as np
import pandas as pd
import os
from selenium import webdriver
from shinywidgets import output_widget, render_widget
import plotly.express as px
import plotly.graph_objs as go

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
bus_isochrones = pd.read_json(os.path.join(data_directory, 'bus_isochrones.json'), orient='records', lines=True)
bicycle_isochrones = pd.read_json(os.path.join(data_directory, 'bicycle_isochrones.json'), orient='records', lines=True)
mrt_isochrones = pd.read_json(os.path.join(data_directory, 'mrt_isochrones.json'), orient='records', lines=True)
public_transport_isochrones = pd.read_json(os.path.join(data_directory, 'public_isochrones.json'), orient='records', lines=True)
mrt_names = mrt_df['MRT.Name'].values.tolist()
coords = mrt_df[['Latitude', 'Longitude']].values.tolist()

app_ui = ui.page_fluid(
    ui.h2("Transport Medium"),
    ui.input_select(
        "transport_means",
        "Select the means of movement",
        ["Bus", "Bicycle", "MRT", "Public_Transport"]
    ),
    ui.input_selectize(
        "station",
        "Select the MRT station",
        mrt_names,
        multiple=True
    ),
    # Set step to 5 for intervals of 5 minutes
    ui.input_slider(
        "n_min",
        "Select Maximum Time (in minutes)",
        min=10, max=60, value=5, step=5
    ),
    ui.output_text_verbatim("txt"),
    output_widget("plot")
)


def server(input, output, session):
    def get_isochrone(name, mode, cutoff):
        variable_name = f"{mode}_isochrones"    
        df = globals()[variable_name] 
        filtered_df = df[(df['MRT.Name'] == name)]
        isochrone = filtered_df[f'isochrone_{cutoff}M'].iloc[0]
        return isochrone


    @render.text
    def txt():
        return f"You are trying to find the maximum distance that can be travelled by {input.transport_means()}\nfrom {input.station()}\nwithin {input.n_min()} minutes"
    
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
            # Extracting color and coordinates for the current MRT station
            station_row = mrt_df[mrt_df['MRT.Name'] == mrt_name].iloc[0]
            color = station_row["Color"]
            lat, lon = station_row['Latitude'], station_row['Longitude']
            
            # Convert cutoff to minutes, e.g. "15M" to 15
            cutoff = int(input.n_min())
            
            # Fetch the isochrone data
            isochrone = get_isochrone(name=mrt_name, mode=input.transport_means().lower(), cutoff=cutoff)
            lon_coords = [coord[0] for coord in isochrone]
            lat_coords = [coord[1] for coord in isochrone]
                
            # Add isochrone as a trace
            fig.add_trace(go.Scattermapbox(
                mode="lines",
                lon=lon_coords,
                lat=lat_coords,
                name=f"Isochrone {lat}, {lon}",
                line=dict(width=1, color=color),
                fill="toself"
            ))
            # Add MRT station as a marker
            fig.add_trace(go.Scattermapbox(
                mode="markers",
                lon=[lon],
                lat=[lat],
                text=[mrt_name],
                name=mrt_name,
                marker=dict(size=10, color=color),
                textposition="bottom center"
            ))

        # Update the layout to match the provided example
        fig.update_layout(
            mapbox_style="carto-positron",
            mapbox_zoom=12,
            mapbox_center={"lat": coords[0][0], "lon": coords[0][1]},
            showlegend=False
        )

        # Show the figure
        return fig
            

app = App(app_ui, server)
if __name__ == "__main__":
    app.run()
