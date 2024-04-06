from shiny import App, reactive, render, ui
from shinywidgets import output_widget, register_widget
import plotly.graph_objects as go
import os
import json
import shapely
import geopandas as gpd
import pandas as pd
from myUtils import prepData, createMap, city_centers, get_zoom
import csv
import numpy as np


subZoneScore, parkConnector_lats, parkConnector_lons, cyclingPath_lats, cyclingPath_lons, bicycleParking, hazards = prepData()

city_centers = city_centers(subZoneScore)
area = subZoneScore[['SUBZONE_N','SHAPE_Area']]
score = subZoneScore[['SUBZONE_N','score']]

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
                    selected = ["Index"]#, "ParkC", "CyclingP", "BicycleP", "Hazards"]
                ),
            ),
            ui.input_select( 
                "select",
                "Focus on Subzone",
                choices=list(city_centers.keys())
            ),
            ui.input_slider(
                "n_min",
                "Adjust Parameters",
                min=10, max=60, value=5, step=5
            )
        ),
    ),
    ui.panel_well(
        ui.row(
            ui.output_text_verbatim("txt")
        )
    ),
        output_widget("map")
)



def server(input, output, session):

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
        sel = input.select()
        map.layout.mapbox.center = city_centers[sel]
        map.layout.mapbox.zoom = get_zoom(subZoneScore.loc[subZoneScore['SUBZONE_N']==sel, 'geometry'].values[0]) # np.log(area.loc[area['SUBZONE_N']==sel, 'SHAPE_Area'].values[0])

        @render.text
        def txt():
            return f"{sel} has {'good' if score.loc[score['SUBZONE_N']==sel, 'score'].values[0] >0.5 else 'bad'} cycling infrastrucure overall. It is ranked XXXX"
#pop up showing recommendations for subzone

app = App(app_ui, server)

