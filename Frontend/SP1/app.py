from shiny import App, reactive, render, ui
from shinywidgets import output_widget, register_widget #render_plotly,render_widget 
import plotly.graph_objects as go
import os
import json
import shapely
import geopandas as gpd
import pandas as pd
from myUtils import prepData, createMap
import csv

# current_directory = os.getcwd()
# data_directory = os.path.join(current_directory, 'data') #../../
# file_path1 = os.path.join(data_directory, 'subZoneScore.csv')
# subZoneScore = pd.read_csv(file_path1)
# subZoneScore['geometry'] = subZoneScore['geometry'].apply(shapely.from_wkt)
# subZoneScore = gpd.GeoDataFrame(subZoneScore)

city_centers = {
    "Placeholder": (103.9, 1.38),
    "Paris": (104, 1.40),
    "New York": (103.8, 1.36)
}
subZoneScore, parkConnector_lats, parkConnector_lons, cyclingPath_lats, cyclingPath_lons, bicycleParking, hazards = prepData()


app_ui = ui.page_fluid(
    # title
    ui.h1("Singapore Map of Index Findings"),
    ui.p("Explaination of data source, legends, why features, etc", style = "max-width:1000px"),
    ui.h4("Use the buttons below to customise plots."),

    # UI
    ui.panel_well(
        ui.row(
            ui.column(3, 
                ui.input_checkbox_group(
                    "toggle", "Show/Hide data layers", {"Index": "Index Scores", "ParkC": "Park Connector", "CyclingP": "Cycling Path", "BicycleP": "Bicycle Parking", "Hazards": "Hazards"},
                    selected = ["Index", "ParkC", "CyclingP", "BicycleP", "Hazards"]
                ),
            ),
            ui.input_select( 
                "center",
                "Focus on Subzone",
                choices=list(city_centers.keys())
            ),
            # Set step to 5 for intervals of 5 minutes
            ui.input_slider(
                "n_min",
                "Adjust Parameters",
                min=10, max=60, value=5, step=5
            )
        )
    ),
    output_widget("map")
)



def server(input, output, session):


    #@output
    #@render_widget
    
    # @render_plotly
    # def plot():
    map = createMap(subZoneScore, parkConnector_lats, parkConnector_lons, cyclingPath_lats, cyclingPath_lons, bicycleParking, hazards)
    register_widget("map", map)

    @reactive.Effect
    def _():
        showI = 'Index' in input.toggle()
        showP = 'ParkC' in input.toggle()
        showC = 'CyclingP' in input.toggle()
        showB = 'BicycleP' in input.toggle()
        showH = 'Hazards' in input.toggle()
        map.data[0].visible = showI
        map.data[1].visible = showP
        map.data[2].visible = showC
        map.data[3].visible = showB
        map.data[4].visible = showH


app = App(app_ui, server)