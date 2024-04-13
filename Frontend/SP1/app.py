from shiny import App, reactive, render, ui
from shinywidgets import output_widget, register_widget
import plotly.graph_objects as go
import os
import json
import shapely
import geopandas as gpd
import pandas as pd
from myUtils import prepData, createMap, city_centers, get_zoom, get_filter_areas
import csv
import numpy as np


subZoneScore, parkConnector_lats, parkConnector_lons, cyclingPath_lats, cyclingPath_lons, bicycleParking, hazards = prepData()

region, planning_area, planning_area_central, planning_area_east, planning_area_north, planning_area_north_east, planning_area_west = get_filter_areas()
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
                    "toggle", "Show/Hide data layers", {"Index": "Index Scores", "ParkC": "Park Connector", "CyclingP": "Cycling Path", "BicycleP": "Bicycle Parking", "Hazards": "Choke Points"},
                    selected = ["Index"]
                )
            ),
            ui.column(3, 

                ui.input_select( 
                    "select_planning_area",
                    "Select Planning Area",
                    choices=planning_area
                ),
                ui.input_select( 
                    "select_subzone",
                    "Focus on Subzone",
                    choices=list(city_centers.keys()),
                )
            ),
            ui.input_slider(
                "n_min",
                "Adjust Parameters",
                min=10, max=60, value=5, step=5
            )
        )
    ),
        ui.panel_well(
            ui.row(
                ui.output_text_verbatim("txt")
        )),
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

        # sel_region = input.select_region()
        # if sel_region == 'CENTRAL REGION':
        #     planning_area = planning_area_central
        # elif sel_region == 'EAST REGION':
        #     planning_area = planning_area_east
        # elif sel_region == 'NORTH REGION':
        #     planning_area = planning_area_north
        # elif sel_region == 'NORTH-EAST REGION':
        #     planning_area = planning_area_north_east
        # elif sel_region == 'WEST REGION':
        #     planning_area = planning_area_west
        # else: planning_area = ["Error, please select another region"]
        # ui.update_select(
        #     "select_planning_area",
        #     choices=planning_area,)
        sel_planning_area = input.select_planning_area()
        subzones = subZoneScore.loc[subZoneScore['PLN_AREA_N']== sel_planning_area, 'SUBZONE_N'].unique().tolist()
        subzones.sort()
        ui.update_select(
            "select_subzone",
            choices=subzones,)

    @reactive.Effect()
    def react():
        sel = input.select_subzone()
        map.layout.mapbox.center = city_centers[sel]
        map.layout.mapbox.zoom = get_zoom(subZoneScore.loc[subZoneScore['SUBZONE_N']==sel, 'geometry'].values[0])

        @render.text
        def txt():
            name = sel.title()
            overallRank = subZoneScore.loc[subZoneScore['SUBZONE_N']==sel, 'Rank'].values[0]
            if subZoneScore.loc[subZoneScore['SUBZONE_N']==sel, 'score'].values[0] > 0.4 :
                goodbad = 'good'
            elif subZoneScore.loc[subZoneScore['SUBZONE_N']==sel, 'score'].values[0] > 0.3:
                goodbad = 'average'
            else: goodbad = 'bad'
            
            if subZoneScore.loc[subZoneScore['SUBZONE_N']==sel, 'TotalCyclingPathRank'].values[0] >= 139:
                lanes = 'has no cycling paths. Needs much improvement.'
            elif subZoneScore.loc[subZoneScore['SUBZONE_N']==sel, 'TotalCyclingPathRank'].values[0] <= 35:
                lanes = 'has good amount of cycling paths!'
            else:
                lanes = 'has little amount of cycling paths. Could use some improvement.'

            if subZoneScore.loc[subZoneScore['SUBZONE_N']==sel, 'BicycleParkingRank'].values[0] <= 45:
                bicyclepark = 'has great amount of bicycle parking!'
            else:
                bicyclepark = 'has an average amount of bicycle parking.'

            if subZoneScore.loc[subZoneScore['SUBZONE_N']==sel, 'ChokePointNormRank'].values[0] == 1:
                chokept = 'has no chokepoints!'
            elif subZoneScore.loc[subZoneScore['SUBZONE_N']==sel, 'ChokePointNormRank'].values[0] >= 300:
                chokept = 'has a lot of chokepoints as compared to other subzones.'
            else:
                chokept = 'has an average amount of chokepoints.'

            return f"{name} is ranked {overallRank} overall.\nThis is considered {goodbad} cycling infrastrucure overall. \n{name} {lanes} \n{name} {bicyclepark} \n{name} {chokept}"

#pop up showing recommendations for subzone

app = App(app_ui, server)

