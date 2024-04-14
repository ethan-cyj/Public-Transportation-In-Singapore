from shiny import App, render, ui, session, Inputs, Outputs, reactive
from sklearn.cluster import KMeans
from shiny import App, render, ui
from shinyswatch import theme
import pandas as pd
import os
from shinywidgets import output_widget, render_widget, register_widget
import plotly.graph_objs as go
import geopandas as gpd
from shapely import Point
import shapely
import csv
import json 
import app_utils as utils
from itables.shiny import DT
from bs4 import BeautifulSoup
import polyline
import plotly.io as pio
from pathlib import Path
from shiny.types import ImgData
import numpy as np
from dotenv import load_dotenv
import requests

load_dotenv()
#initialise OneMap object here
# one_map_email = os.getenv("ONE_MAP_EMAIL")
# one_map_password = os.getenv("ONE_MAP_PASSWORD")
# payload = {
#             "email": one_map_email,
#             "password": one_map_password
#         }
# api_key = requests.request("POST", "https://www.onemap.gov.sg/api/auth/post/getToken", json=payload)
# api_key = api_key.json()["access_token"]
# print(api_key)
api_key = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiI0NmJkYTI0NmI1NmM4ZDY5YWMyYzEyNmI2ZjEyOGU0MyIsImlzcyI6Imh0dHA6Ly9pbnRlcm5hbC1hbGItb20tcHJkZXppdC1pdC0xMjIzNjk4OTkyLmFwLXNvdXRoZWFzdC0xLmVsYi5hbWF6b25hd3MuY29tL2FwaS92Mi91c2VyL3Nlc3Npb24iLCJpYXQiOjE3MTI0Njk0MDQsImV4cCI6MTcxMjcyODYwNCwibmJmIjoxNzEyNDY5NDA0LCJqdGkiOiJRTWdrc3M2ZUlXNUd0OVFZIiwidXNlcl9pZCI6MjkxNCwiZm9yZXZlciI6ZmFsc2V9.GAjjMnx10GYzfZ2H4UWUQTZVYRAfO61Bet_eznqL7zI"
current_directory = os.getcwd()
data_directory = os.path.join(current_directory, 'data')
www_dir = os.path.join(current_directory, 'Frontend','www')

#Ranking Plot Preparation
pio.templates.default = "simple_white"


#SP1 File Reading
subZoneScore, parkConnector_lats, parkConnector_lons, cyclingPath_lats, cyclingPath_lons, bicycleParking, hazards = utils.prepData()
region, planning_area, planning_area_central, planning_area_east, planning_area_north, planning_area_north_east, planning_area_west = utils.get_filter_areas()
city_centers = utils.city_centers(subZoneScore)
area = subZoneScore[['SUBZONE_N','SHAPE_Area']]
score = subZoneScore[['SUBZONE_N','score']]

#SP2 File Reading
basemap,cluster_ranking = utils.SP2_prep_Chloropeth_Map()
Centroid_MRT_df = utils.SP2_Prep_Centroid_MRT_Metrics()

#SP3 File Reading
isochrone_directory = os.path.join(current_directory, 'data/Isochrone_data')
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
bus_isochrones = pd.read_json(os.path.join(isochrone_directory, 'bus_isochrones_new.json'), orient='records', lines=True)
bicycle_isochrones = pd.read_json(os.path.join(isochrone_directory, 'bicycle_isochrones_new.json'), orient='records', lines=True)
mrt_isochrones = pd.read_json(os.path.join(isochrone_directory, 'mrt_isochrones_new.json'), orient='records', lines=True)
public_transport_isochrones = pd.read_json(os.path.join(isochrone_directory, 'public_isochrones_new.json'), orient='records', lines=True)
mrt_names = mrt_df['MRT.Name'].values.tolist()
coords = mrt_df[['Latitude', 'Longitude']].values.tolist()



app_ui = ui.page_navbar(
    theme.minty(),
    ui.nav_panel("Sub-Problem 1: Cycling Infrastructure Suitability Index", 
                # Title and Background
                ui.row(
                    ui.column(7,
                              ui.h2("Which Subzone has Good/Bad Cycling Infrastructure?")),
                    ui.column(5,
                              ui.input_action_button("sp1_help_button", "Instructions", class_ = "btn-danger"))
                ),
                # UI
                ui.page_sidebar(
                    ui.sidebar(
                        ui.input_checkbox_group(
                            "toggle", "Show/Hide data layers", {"Index": "Index Scores", "ParkC": "Park Connector", "CyclingP": "Cycling Path", "BicycleP": "Bicycle Parking", "Hazards": "Choke Points"},
                            selected = ["Index"]
                        ),
                        ui.input_select( 
                            "select_planning_area",
                            "Select Planning Area",
                            choices=planning_area
                        ),
                        ui.input_select( 
                            "select_subzone",
                            "Focus on Subzone",
                            choices=list(city_centers.keys()),
                        ),
                        ui.input_action_button("sp1_generate_table", "Zoom In to Location", class_ = "btn-success"),
                        ),
                    ui.panel_well(
                    ui.row(
                        ui.output_text_verbatim("txtsp1")
                        )
                    ),
                    output_widget("map")
                ),
                
            ),

    ui.nav_panel("Sub-Problem 2: Last Mile Accessibility Index",
                ui.navset_tab(
                    ui.nav_panel("For Policy Makers",
                                 ui.page_sidebar(
                                     ui.sidebar(
                                        ui.input_action_button("sp2_help_button", "Instructions", class_ = "btn-danger"),
                                        ui.input_select("metrics", 
                                                        "Select Metric for Comparison", 
                                                        choices=["Distance","Suitability", "Time Savings", 'Time Savings (Log)',"Weighted Score"],
                                                        selected = "Distance"),
                                        ui.input_action_button("help_button", "Definition of Metric", class_ = "btn-dark"),
                                        ui.input_switch("exclude",
                                                        "Exclude Changi & Tuas",
                                                        value = False)
                                         ),
                                    ui.row(
                                    ui.column(8, ui.h2("Rankings by Planning Area using Nearest 5-Cluster Method")),
                                    ui.column(4,ui.input_action_button("rationale_button", "Why 5 Clusters?", class_ = "btn-info"))
                                    ),
                                    ui.row(
                                        ui.column(6, ui.card(
                                            ui.card_header("Map of Raw Values",
                                                style="color:white; background:#2A2A2A !important;"),
                                                output_widget("chloropeth_map")
                                            )),
                                        ui.column(6,ui.card(
                                            ui.card_header("Ranking Plot of Districts",
                                                style="color:white; background:#2A2A2A !important;"),
                                            output_widget("plot_planning_area_rankings")
                                            ))
                                    )
                                 )
                    ),
                    ui.nav_panel("For Prospective Cyclists",
                        ui.h2("Analysis of Path Metrics from MRT/LRT stations to Residential Centroids"),
                        ui.page_sidebar(
                            ui.sidebar(
                                ui.input_action_button("instructions_button", "Instructions", class_ = "btn-danger"),
                                ui.input_numeric("w1", "Weight for Distance", value=0.25, min=0, max=1, step=0.1),
                                ui.input_numeric("w2", "Weight for Suitability", value=0.25, min=0, max=1, step=0.1),
                                ui.input_numeric("w3", "Weight for Time Savings", value=0.25, min=0, max=1, step=0.1),
                                ui.input_numeric("w4", "Weight for Steepness", value=0.25, min=0, max=1, step=0.1),
                                ui.help_text("Note: Weights should sum to 1.0"),
                                ui.input_action_button("weight_sum_btn", "Verify Sum of Weights", class_ = "btn-dark"),
                                ui.output_text_verbatim("check_sum"),
                                ui.input_action_button("generate_table", "Generate Table", class_ = "btn-success"),
                                ui.input_text("user_address","Input an address to retrieve closest Residential Cluster.",placeholder="eg. Havelock Road"),
                                ui.input_action_button("plot_route", "Generate Route", class_ = "btn-default"),
                            ),
                            ui.card(
                                ui.card_header("Scores of Points of Interest",
                                                style="color:white; background:#2A2A2A !important;"),
                                ui.output_ui("centroid_mrt_metrics")
                            ),
                            ui.tags.link(
                                rel="stylesheet",
                                href="https://fonts.googleapis.com/css?family=Roboto"
                            ),

                            ui.tags.style(
                                "body { font-family: 'Roboto', sans-serif; }"
                            ),
                            ui.layout_columns(
                                ui.card(
                                    ui.card_header("Route Directions",
                                                   style="color:white; background:#2A2A2A !important;"),
                                    ui.value_box(
                                        title = "",
                                        value = ui.output_text_verbatim("route_instructions"),
                                        full_screen = True
                                    )
                                ),
                                ui.card(
                                    ui.card_header("Suggested Route on Map",
                                                   style="color:white; background:#2A2A2A !important;"),
                                    output_widget("plot_path")
                                )
                            )
                        )
                    )
                )),
    ui.nav_panel("Sub-Problem 3: Isochrone Analysis",
                 ui.row(
                    ui.column(6,
                              ui.h2("Distance Travellable from MRT/LRT Stations")),
                    ui.column(6,
                              ui.input_action_button("sp3_help_button", "Instructions", class_ = "btn-danger"))
                ),
                ui.page_sidebar(
                ui.sidebar(ui.input_selectize(
                    "transport_means",
                    "Select the Means of Movement (Limit to 2 Options)",
                    ["Bus", "Bicycle", "MRT", "Public Transport"],
                    multiple=True,
                    options = dict(maxItems = 2),
                ),ui.input_selectize(
                    "station",
                    "Select the MRT/LRT station (Multiple Selection)",
                    mrt_names,
                    multiple=True
                ),
                # Set step to 5 for intervals of 5 minutes
                ui.input_slider(
                    "n_min",
                    "Select Maximum Time (in minutes)",
                    min=10, max=60, value=5, step=5
                ), 
                ui.input_action_button("sp3_generate_isochrones", "Generate Isochrones", class_ = "btn-success"),
                bg="#f8f8f8"
                ),
                ui.output_text_verbatim("txt"),
                output_widget("plot")
                )
                ),
    title = ui.output_image("image",inline= True),
    bg= "#20c997"
)


def server(input, output, session):
    #General
    ##Logo
    @render.image
    def image():
        dir = Path(www_dir)
        img: ImgData = {"src": str(dir / "logo1.png"), "width": "120px"}
        return img

    #SP1 Calls
    @reactive.effect
    @reactive.event(input.sp1_help_button)
    async def _():
        m = ui.modal("Use the buttons below to customise the plots. Following that, click on the Checkboxes to toggle map overlays. Finally, Select the Planning Area of choice then the subzone you want to zoom in on.",
                title = "Instructions to using Tab",
                easy_close=True,
                footer = None)
        ui.modal_show(m)
    map = utils.createMap(subZoneScore, parkConnector_lats, parkConnector_lons, cyclingPath_lats, cyclingPath_lons, bicycleParking, hazards)
    register_widget("map", map)
    
    
    @reactive.Effect
    def re():
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
        sel_planning_area = input.select_planning_area()
        subzones = subZoneScore.loc[subZoneScore['PLN_AREA_N']== sel_planning_area, 'SUBZONE_N'].unique().tolist()
        subzones.sort()
        ui.update_select(
            "select_subzone",
            choices=subzones,)
        
    @reactive.Effect()
    @reactive.event(input.sp1_generate_table)
    def react():
        sel = input.select_subzone()
        map.layout.mapbox.center = city_centers[sel]
        map.layout.mapbox.zoom = utils.get_zoom(subZoneScore.loc[subZoneScore['SUBZONE_N']==sel, 'geometry'].values[0])

        @render.text
        def txtsp1():
            name = sel.title()
            overallRank = subZoneScore.loc[subZoneScore['SUBZONE_N']==sel, 'Rank'].values[0]
            if subZoneScore.loc[subZoneScore['SUBZONE_N']==sel, 'score'].values[0] > 0.42 :
                goodbad = 'good'
            elif subZoneScore.loc[subZoneScore['SUBZONE_N']==sel, 'score'].values[0] > 0.32:
                goodbad = 'average'
            else: goodbad = 'bad'
            
            if subZoneScore.loc[subZoneScore['SUBZONE_N']==sel, 'TotalCyclingPathRank'].values[0] >= 139:
                lanes = 'has no cycling paths. Needs much improvement.'
            elif subZoneScore.loc[subZoneScore['SUBZONE_N']==sel, 'TotalCyclingPathRank'].values[0] <= 35:
                lanes = 'has good amount of cycling paths!'
            else:
                lanes = 'has little amount of cycling paths. Could use some improvement.'

            if subZoneScore.loc[subZoneScore['SUBZONE_N']==sel, 'BicycleParkingRank'].values[0] <= 80:
                bicyclepark = 'has great amount of bicycle parking!'
            else:
                bicyclepark = 'has an average amount of bicycle parking.'

            if subZoneScore.loc[subZoneScore['SUBZONE_N']==sel, 'ChokePointNormRank'].values[0] == 1:
                chokept = 'has no chokepoints!'
            elif subZoneScore.loc[subZoneScore['SUBZONE_N']==sel, 'ChokePointNormRank'].values[0] >= 238:
                chokept = 'has a lot of chokepoints as compared to other subzones.'
            else:
                chokept = 'has an average amount of chokepoints.'

            return f"{name} is ranked {overallRank} overall.\nThis is considered {goodbad} cycling infrastrucure overall. \n{name} {lanes} \n{name} {bicyclepark} \n{name} {chokept}"

        
    #SP2 Calls
    #Ranking Plot
    @output
    @render_widget
    def plot_planning_area_rankings():
        main_metric = input.metrics()
        if main_metric == "Time Savings (Log)":
            main_metric = "Time Savings(Log)"
        df = cluster_ranking.groupby('Planning_Area').agg({main_metric:'mean'}).reset_index()
        if input.exclude():
            df = df[~df['Planning_Area'].isin(['CHANGI','TUAS'])]
        df = df.dropna(subset=[main_metric])
        df = df.sort_values(by=main_metric, ascending=False).reset_index(drop=True)
        fig = go.Figure()
        fig.update_layout(title_text='Average ' + main_metric + ' for each Planning Area',
                        yaxis_title=main_metric,
                        hovermode="closest")

        colors = ['#7c8981'] * len(df)
        colors[0:3] = ['#cb2721'] * 3  # Top 3
        colors[-3:] = ['#0b569d'] * 3  # Bottom 3

        hover_texts = [f"Planning Area: {row['Planning_Area']}<br>{main_metric}: {row[main_metric]:.2f}"
                    for _, row in df.iterrows()]
        
        fig.add_trace(go.Bar(x=df['Planning_Area'], y=df[main_metric],
                            marker_color=colors,
                            hoverinfo="text",
                            text=hover_texts))
        fig.update_layout(
            xaxis=dict(showticklabels=False),
            annotations=[]  # Assuming you are not using annotations here, otherwise add your annotations list
        )
        annotations = []
        for i in list(range(3)) + list(range(len(df) - 3, len(df))):
            annotations.append(dict(
                x=df['Planning_Area'].iloc[i],
                y=df[main_metric].iloc[i],
                text=df['Planning_Area'].iloc[i],
                showarrow=True,
                arrowhead=1,
                ax=30,
                ay=-40,
                textangle=-60,
                font=dict(color='red' if i < 3 else 'blue', size=12),
                arrowcolor='red' if i < 3 else 'blue'
            ))

        fig.update_layout(annotations=annotations)
        return fig

    # Reactive button for instructions button
    @reactive.effect
    @reactive.event(input.sp2_help_button)
    async def _():
        m = ui.modal("Select the metric of Comparison (Distance, Suitability, Time Savings, Time Savings (Log), Weighted Score) to view the differences in scores and rankings between districts in Singapore.",
                title = "Instructions to using Tab",
                easy_close=True,
                footer = None)
        ui.modal_show(m)
    
    # Reactive button for button for explanation for why the 5-cluster method is used
    @reactive.effect
    @reactive.event(input.rationale_button)
    async def _():
        m = ui.modal("This method involves obtaining the 5 nearest residential clusters to each MRT and obtaining path metrics through LTA OneMap and OpenrouteService.\nThe mean of the metric of interest for each planning area is then calculated by averaging that metric of all such paths within the planning area. This method is used to obtain the rankings by planning area for the metric of interest.",
                title = "What is the Nearest 5-Cluster Method?",
                easy_close=True,
                footer = None)
        ui.modal_show(m)
    
    # Printing of chloropeth map
    @output 
    @render_widget
    def chloropeth_map():
        x = input.metrics()
        if x == "Time Savings (Log)":
            x = "Time Savings(Log)"
        df = cluster_ranking.groupby('Planning_Area').agg({x:'mean'}).reset_index()
        basemap_modified = pd.merge(basemap, df, left_on='Planning_Area', right_on='Planning_Area', how='left')

        fig = go.Figure()

        fig.add_trace(go.Choroplethmapbox(geojson=json.loads(basemap_modified.geometry.to_json()), 
                                   locations=basemap_modified.index,
                                   z=basemap_modified[x],
                                   name = input.metrics(),
                                   visible = not input.exclude(),
                                   colorscale='RdYlGn',
                                   hoverinfo = 'text',
                                   text = ("Planning Area: " + basemap_modified['Planning_Area'] + '<br>' + 
                                           "Average " + input.metrics() + " of Paths Within the Area: " + round(basemap_modified[x],2).astype(str) )))
        
        basemap_modified_exclude = basemap_modified[~basemap_modified['Planning_Area'].isin(['CHANGI','TUAS'])]

        fig.add_trace(go.Choroplethmapbox(geojson=json.loads(basemap_modified_exclude.geometry.to_json()), 
                                   locations=basemap_modified_exclude.index,
                                   z=basemap_modified_exclude[x],
                                   name = input.metrics() + "2",
                                   colorscale='RdYlGn',
                                   visible= input.exclude(),
                                   hoverinfo = 'text',
                                   text = ("Planning Area: " + basemap_modified_exclude['Planning_Area'] + '<br>' + 
                                           "Average " + input.metrics() + " of Paths Within the Area: " + round(basemap_modified_exclude[x],2).astype(str) )))        

        fig.update_layout(
            margin={'l':0,'t':0,'b':0,'r':0},
            mapbox={
                'style': "open-street-map",
                'center': {'lat': 1.36, 'lon': 103.85},
                'zoom':9
            }
        )
        return fig
    
    # Reactive effect for the help button to explain the corresponding metric selected by the user
    @reactive.effect
    @reactive.event(input.help_button)
    async def _():
        if input.metrics() == "Distance":
            m = ui.modal("""The Distance metric describes the distance from transport stations to residential centroids (in km),
                        and is measured by the aggregate mean of all such distances within the planning area"""
                        ,
                    title = "Definition of Metric",
                    easy_close=True,
                    footer = None)
        elif input.metrics() == "Suitability":
            m = ui.modal("""The Suitability metric quantifies the suitability of paths (out of 10) from transport stations to residential centroids (Obtained from ORS) and
                         is computed based on characteristics of the route and the profile of the area.
                        It is measured by the aggregate mean of all such suitability of paths within the planning area"""
                        ,
                    title = "Definition of Metric",
                    easy_close=True,
                    footer = None)
        elif input.metrics() == "Time Savings":
            m = ui.modal("""The Time Savings metric quantifies the time savings of paths (in minutes) from transport stations to residential centroids through the formula
                         Time Savings = Time Taken by Public Transport - Time Taken by Cycling. The value shows aggregate mean of all such time savings of paths within the planning area"""
                        ,
                    title = "Definition of Metric",
                    easy_close=True,
                    footer = None)
        elif input.metrics() == "Weighted Score":
            m = ui.modal("""The Weighted Score metric quantifies overall score of the district (normalised from a score out of 100) based on the other metrics provided. 
                         The value shows aggregate mean of all such time savings of paths within the planning area"""
                        ,
                    title = "Definition of Metric",
                    easy_close=True,
                    footer = None)
        else:
            m = ui.modal("""The Time Savings (Log) metric is the same as the time savings variable, except that the values are the log values of the time savings.
            It is computed by the aggregate mean of all such time savings of paths within the planning area""",
            title = "Definition of Metric",
                    easy_close=True,
                    footer = None)
        ui.modal_show(m)
    
    # Reactive effect for the instruction button to tell users to input their weights
    @reactive.effect
    @reactive.event(input.instructions_button)
    async def _():
        m = ui.modal("""Adjust the weights to calculate the weighted score for paths connecting residential centroids to their nearest MRT/LRT station. Following that, press the Verify Sum of Weights button to verify the weight sum, before pressing the Generate Table button to show the scores. 
                     From the Data Table, plot the suggested route from the map through the inputting of the row number before pressing the Generate Route button.
                     """,
                title = "Instructions to compute path metrics",
                easy_close=True,
                footer = None)
        ui.modal_show(m)

    # Reactive effect for weight sum button to compute the sum of weights inputted by the user
    @reactive.Calc
    @reactive.event(input.weight_sum_btn)
    def weight_sum_btn():
        input.weight_sum_btn()
        sum_weights = input.w1() + input.w2() + input.w3() + input.w4()
        return(sum_weights)
    
    # Reactive effect to check the sum of weights inputted by the user that it is equal to 1
    @render.text
    def check_sum():
        x = weight_sum_btn()
        tolerance = 1e-10  # Set a small tolerance
        if abs(x - 1.0) < tolerance:
            return "Sum of Weights = 1.0" 
        else:
            m = ui.modal("""Sum of Weights is not equal to 1. Please try again.""",
                    title = "Invalid Weights Sum",
                    easy_close=True,
                    footer = None)
            ui.modal_show(m)
            return "Sum is NOT 1.0"
    
    # Reactive effect to generate data table if the weight sum is equal to 1
    @render.ui
    @reactive.event(input.generate_table)
    def centroid_mrt_metrics():
        x = weight_sum_btn()
        tolerance = 1e-10  # Set a small tolerance
        if abs(x - 1.0) > tolerance:
            m = ui.modal("Sum of Weights is not equal to 1. Please try again.",
                    title = "Invalid Weights Sum",
                    easy_close=True,
                    footer = None)
            ui.modal_show(m)
            return "Input Weights Correctly to View Data Table."
        else:
            Centroid_MRT_df['weighted_score'] = utils.calculate_weighted_score(Centroid_MRT_df,input.w1(),input.w2(),input.w3(),input.w4())
            output = Centroid_MRT_df.copy(deep =True)
            output.rename(columns = {'weighted_score':'Weighted Score (/100)',
                                    'centroid_name':'Point of Interest',
                                    'MRT.Name':'Station',
                                    'Planning_Area':'Planning Area',
                                    'distance':'Cycling Distance (km)',
                                    'suitability':'Suitability (/10)',
                                    'time_difference':'Time Savings (min)',
                                    'steepness':'Steepness (/5)'},inplace = True)
            numeric_cols = output.select_dtypes(include=[np.number]).columns
            output[numeric_cols] = output[numeric_cols].round(3)
            with pd.option_context('display.float_format', '{:.3f}'.format):
                return ui.HTML(DT(output[['Weighted Score (/100)', 'Point of Interest', 'Station', 'Planning Area', 'Cycling Distance (km)', 'Suitability (/10)', 'Time Savings (min)', 'Steepness (/5)']], filters=True, maxBytes=0, showIndex=True))
    
    # Reactive effect to plot path given a valid input
    @render_widget
    @reactive.event(input.plot_route)
    def plot_path():
        user_input = utils.SP2_get_centroid_from_postal_code(input.user_address())
        # Condition for invalid inputs to generate a pop-up for invalid addresses
        if not user_input:
            m = ui.modal("Invalid Input",
                    title = "Input returned no results, try a different address!",
                    easy_close=True,
                    footer = None)
            ui.modal_show(m)
            return "Input returned no results, try a different address!"
        else:
            print("User Input: ", type(user_input), user_input)
            
            latitude = float(user_input[0])
            longitude = float(user_input[1])
            row = Centroid_MRT_df[(Centroid_MRT_df['Latitude_x'] == latitude) & (Centroid_MRT_df['Longitude_x'] == longitude)].iloc[0]
            print("Row: ", row)
            fig = go.Figure()
            fig.add_trace(go.Scattermapbox(
                lat = [row['Latitude_x']],
                lon = [row['Longitude_x']],
                mode="markers",
                name = "Centroid",
                hoverinfo = "text",
                text = ("Centroid Name:" + row['centroid_name'])
                )   
            )
            fig.add_trace(go.Scattermapbox(
                lat = [row['Latitude_y']],
                lon = [row['Longitude_y']],
                mode="markers",
                name = "Transport Station",
                hoverinfo = "text",
                text = ("Transport Station:" + row['MRT.Name'])
                )
            )
            try:
                route_data = row['cycle_route']['route_geometry']
                route_coordinates = polyline.decode(route_data)
                lats = [point[0] for point in route_coordinates]
                lons = [point[1] for point in route_coordinates]
                fig.add_trace(go.Scattermapbox(
                    mode="lines",
                    lon=lons,
                    lat=lats,
                    marker={'size': 10, 'color': "Blue"},
                    hoverinfo = 'text',
                    text = ("Time difference:" + str(round(row['time_difference'],2)) + " min" + '<br>' +
                            "Distance:" + str(round(row['distance'],3)) + " km"),
                    showlegend= False,
                ))
            except Exception as e:
                pass

            fig.update_layout(
                margin={'l':0,'t':0,'b':0,'r':0},
                mapbox={
                    'style': "open-street-map",
                    'center': {'lat': row['Latitude_x'], 'lon': row['Longitude_x']},
                    'zoom':13
                }
            )
            return fig
    
    # Reactive effect to plot path instructions given a valid input
    @render.text
    @reactive.event(input.plot_route)
    def route_instructions():
        user_input = utils.SP2_get_centroid_from_postal_code(input.user_address())
        if not user_input:
            m = ui.modal("Invalid Input",
                    title = "Input returned no results, try a different address!",
                    easy_close=True,
                    footer = None)
            ui.modal_show(m)
            return "Input returned no results, try a different address!"
        else:
            try:
                print("User Input: ", user_input)
                latitude = float(user_input[0])
                longitude = float(user_input[1])
                row = Centroid_MRT_df[(Centroid_MRT_df['Latitude_x'] == latitude) & (Centroid_MRT_df['Longitude_x'] == longitude)].iloc[0]
                print("Row: ", row)
                route_instructions = row['cycle_route']['route_instructions']
                text = []
                for instruction in route_instructions:
                    text.append(instruction[5] + " " + instruction[9])
                output = '\n'.join(text)
                return output
            except Exception as e:
                return ""
    
    # SP3 Code
    
    # Reactive button for Instructions button for SP3
    @reactive.effect
    @reactive.event(input.sp3_help_button)
    async def _():
        m = ui.modal("Use the buttons in the sidebar to customise the plots. Following that, click on Generate Isochrones button to view your plot!",
                title = "Instructions to using Tab",
                easy_close=True,
                footer = None)
        ui.modal_show(m)
    
    # Get Isochrones for a given MRT name
    def get_isochrone(name, mode, cutoff):
        variable_name = f"{mode}_isochrones"    
        df = globals()[variable_name] 
        filtered_df = df[(df['MRT.Name'] == name)]
        isochrone = filtered_df[f'isochrone_{cutoff}M'].iloc[0]
        return isochrone

    # Printing the text for the inputs selection by the user
    @render.text
    def txt():
        if len(input.transport_means()) == 2:
            transport_means1 = (input.transport_means())[0]
            transport_means2 = (input.transport_means())[1]
            
            # Generate the initial text string
            initial_text = f"You are trying to find the maximum distance that can be travelled within {input.n_min()} minutes by {transport_means1} and {transport_means2} from the following stations:"
            
            # Initialize an empty list to store the lines
            lines = [initial_text]
            
            # Iterate over each station in the tuple
            for station in input.station():
                lines.append(f"• {station.strip()}")
        
            # Join the lines with newline characters
            return '\n'.join(lines)
        else:
            # Generate the initial text string
            initial_text = f"You are trying to find the maximum distance that can be travelled within {input.n_min()} minutes by (Transport Means) from the following stations:"
            # Initialize an empty list to store the lines
            lines = [initial_text]
            # Iterate over each station in the tuple
            for transport_means in input.transport_means():
                lines[0] = f"You are trying to find the maximum distance that can be travelled within {input.n_min()} minutes by {input.transport_means()[0]} from the following stations:"
            for station in input.station():
                lines.append(f"• {station.strip()}")
        
            # Join the lines with newline characters
            return '\n'.join(lines)
    
    def generateMapsp3():
        fig = go.Figure()
        for _, row in mrt_df.iterrows():
            # Updating of MRT map coordinates
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
        fig.update_layout(
                mapbox_style="carto-positron",
                mapbox_zoom=12,
                mapbox_center={"lat": mrt_df[mrt_df["MRT.Name"] == "ESPLANADE MRT STATION"].iloc[0]['Latitude'], "lon": mrt_df[mrt_df["MRT.Name"] == "ESPLANADE MRT STATION"].iloc[0]['Longitude']},
                showlegend=False,
                width=1300,
                height=600
            )
        return fig
    
    fig = generateMapsp3()
    register_widget("plot", fig)

    @reactive.Effect()
    @reactive.event(input.sp3_generate_isochrones)
    def react():        
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
            transportmeans_items = input.transport_means()
            # Fetch and add isochrones for each selected MRT station
            for mrt_name in input.station():
                for transport_means in input.transport_means():
                    transport_ind = transportmeans_items.index(transport_means)
                    if transport_ind == 0:
                        thickness = 1
                    else:
                        thickness = 5
                    if transport_means == "Public Transport":
                        transport_means = "Public_Transport"
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
                        line=dict(width=thickness, color=color),
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
                        marker=dict(size=10, color='black'),
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
            if len(input.transport_means()) == 2:
                transportmeans1 = input.transport_means()[0]
                transportmeans2 = input.transport_means()[1]
                legend_items = {transportmeans1: {'color': 'black', 'width': 1}, transportmeans2: {'color': 'black', 'width': 5}}
                legend_box = go.layout.Shape(
                    type="rect",
                    x0=0.80,
                    y0=0.8,
                    x1=0.98,
                    y1=0.95,
                    fillcolor="white",
                    opacity=1,
                    line=dict(width=1)
                )
                fig.add_shape(legend_box)
                for i, (label, style) in enumerate(legend_items.items()):
                    fig.add_shape(type='line', x0=0.82, y0=0.9-0.05*i, x1=0.86, y1=0.9-0.05*i,
                        line=dict(color=style['color'], width=style['width']))
                    fig.add_annotation(x=0.87, y=0.9-0.05*i, xanchor='left', yanchor='middle',
                                    text=label,
                                    showarrow=False, font=dict(size=14, color='black'))
            
            # Show the figure
            return fig
            

app = App(app_ui, server)
if __name__ == "__main__":
    app.run()