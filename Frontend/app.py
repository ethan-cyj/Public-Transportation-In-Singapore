from shiny import App, render, ui, session, Inputs, Outputs, reactive
from sklearn.cluster import KMeans
from shinyswatch import theme
import numpy as np
import pandas as pd
import os
from selenium import webdriver
from shinywidgets import output_widget, render_widget
import plotly.express as px
import plotly.graph_objs as go
import json 
import app_utils as utils
from itables.shiny import DT

current_directory = os.getcwd()
data_directory = os.path.join(current_directory, 'data')

#SP1 File Reading


#SP2 File Reading
basemap,cluster_ranking = utils.SP2_prep_Chloropeth_Map()
Centroid_MRT_df = utils.SP2_Prep_Centroid_MRT_Metrics()

#SP3 File Reading
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


app_ui = ui.page_navbar(
    theme.minty(),
    ui.nav_panel("Sub-Problem 1: Cycling infrastructure suitability index","a"),
    ui.nav_panel("Sub-Problem 2: Last Mile Acessibility Index",
                ui.navset_tab(
                    ui.nav_panel("For Policy Makers",
                        ui.h2("Rankings by Planning Area using nearest 5 cluster method"),
                        ui.help_text(
                                    '''
                                    What is nearest 5 cluster method? This method involves obtaining the 5 nearest residential clusters to each MRT and obtaining path metrics through LTA OneMap and OpenrouteService. 
                                    The mean of the metric of interest for each planning area is then calculated by averaging that metric of all such paths within the planning area. This method is used to obtain the rankings by planning area for the metric of interest.
                                    '''
                                     ),
                        ui.row(
                            ui.column(3,ui.input_select("metrics", 
                                                        "Select Metric for Comparison", 
                                                        choices=["Distance","Suitability", "Time Savings", 'Time Savings(Log)',"Weighted Score"],
                                                        selected = "Distance")),
                            ui.column(3,ui.input_checkbox("exclude",
                                                          "Exclude Changi & Tuas",
                                                          value = False)),
                            ui.column(6,ui.card(ui.output_text("Metric_Description")))                              
                        ),
                        ui.row(
                            ui.layout_columns(
                                ui.card(
                                    output_widget("chloropeth_map")
                                ),
                                ui.card(
                                    ui.p("placeholder")
                                )
                            )
                        )
                    ),
                    ui.nav_panel("For Prospective Cyclists",
                        ui.h2("Table of path metrics for paths of indivual transport stations to residential centroids"),
                        ui.help_text("Filter,sort, and adjust the weights to calculate the weighted score for paths connecting residential centroids to their nearest MRT/LRT station"),
                        ui.page_sidebar(
                            ui.sidebar(
                                ui.input_numeric("w1", "Weight for Distance", value=0, min=-1, max=0, step=0.1),
                                ui.input_numeric("w2", "Weight for Suitability", value=0, min=0, max=1, step=0.1),
                                ui.input_numeric("w3", "Weight for Time Savings", value=0, min=0, max=1, step=0.1),
                                ui.input_numeric("w4", "Weight for Steepness", value=0, min=-1, max=0, step=0.1),
                                ui.help_text("Note: Weights should sum to 1.0"),
                                ui.output_text_verbatim("check_sum")
                            ),
                            ui.card(
                                ui.output_ui("centroid_mrt_metrics")
                            )
                        )
                    )
                )
    ),
    ui.nav_panel("Sub-Problem 3: Isochrone Analysis",
                ui.h2("Distance Travellable from MRT/LRT Stations"),
                ui.page_sidebar(
                ui.sidebar(ui.input_select(
                    "transport_means",
                    "Select the means of movement",
                    ["Bus", "Bicycle", "MRT", "Public_Transport"]
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



    #SP2 Calls
    @output 
    @render_widget
    def chloropeth_map():
        df = cluster_ranking.groupby('Planning_Area').agg({input.metrics():'mean'}).reset_index()
        basemap_modified = pd.merge(basemap, df, left_on='Planning_Area', right_on='Planning_Area', how='left')

        fig = go.Figure()

        fig.add_trace(go.Choroplethmapbox(geojson=json.loads(basemap_modified.geometry.to_json()), 
                                   locations=basemap_modified.index,
                                   z=basemap_modified[input.metrics()],
                                   name = input.metrics(),
                                   visible = not input.exclude(),
                                   colorscale='RdYlGn',
                                   hoverinfo = 'text',
                                   text = ("Planning Area: " + basemap_modified['Planning_Area'] + '<br>' + 
                                           "Average " + input.metrics() + " of Paths Within the Area: " + round(basemap_modified[input.metrics()],2).astype(str) )))
        
        basemap_modified_exclude = basemap_modified[~basemap_modified['Planning_Area'].isin(['CHANGI','TUAS'])]

        fig.add_trace(go.Choroplethmapbox(geojson=json.loads(basemap_modified_exclude.geometry.to_json()), 
                                   locations=basemap_modified_exclude.index,
                                   z=basemap_modified_exclude[input.metrics()],
                                   name = input.metrics() + "2",
                                   colorscale='RdYlGn',
                                   visible= input.exclude(),
                                   hoverinfo = 'text',
                                   text = ("Planning Area: " + basemap_modified_exclude['Planning_Area'] + '<br>' + 
                                           "Average " + input.metrics() + " of Paths Within the Area: " + round(basemap_modified_exclude[input.metrics()],2).astype(str) )))        

        fig.update_layout(
            margin={'l':0,'t':0,'b':0,'r':0},
            mapbox={
                'style': "open-street-map",
                'center': {'lat': 1.36, 'lon': 103.85},
                'zoom':9
            }
        )
        return fig

    @render.ui
    def centroid_mrt_metrics():
        Centroid_MRT_df['weighted_score'] = utils.calculate_weighted_score(Centroid_MRT_df,input.w1(),input.w2(),input.w3(),input.w4())
        return ui.HTML(DT(Centroid_MRT_df[['weighted_score','centroid_name','MRT.Name','Planning_Area','distance','suitability','time_difference','steepness','Latitude_x','Longitude_x','Latitude_y','Longitude_y']],filters=True, maxBytes = 0))
        
    @render.text
    def check_sum():
        sum_weights = input.w1() + input.w2() + input.w3() + input.w4()
        tolerance = 1e-10  # Set a small tolerance
        if abs(sum_weights - 1.0) < tolerance:
            return "Acceptable : Weights sum to 1.0" 
        else:
            return "WARNING : Weights do not sum to 1.0"

    @render.text
    def Metric_Description():
        if input.metrics() == "Distance":
            return (
            """
            Distance: The distance from transport stations to residential centroids
            The aggregate mean of all such distances within the planning area
            """
            )
        elif input.metrics() == "Suitability":
            return (
                '''
                Suitability: The suitability of paths from transport stations to residential centroids(Obtained from ORS).
                Judges how suitable the way is based on characteristics of the route and the profile
                The aggregate mean of all such suitability of paths within the planning area
                '''
            )     
        elif input.metrics() == "Time Savings":
            return (
                '''
                Time Savings: The time savings of paths -(cycle timing - public transport transit timing) from transport stations to residential centroids.
                The aggregate mean of all such time savings of paths within the planning area
                '''
            )
        else:
            return (
                '''
                Time Savings (Log): The log of the time savings of paths -(cycle timing - public transport transit timing) from transport stations to residential centroids.
                The aggregate mean of all such time savings of paths within the planning area
                ''' 
            )
    
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