from shiny import App, render, ui, session, Inputs, Outputs, reactive
from sklearn.cluster import KMeans
from shiny import App, render, ui
from shinyswatch import theme
import pandas as pd
import os
from shinywidgets import output_widget, render_widget
import plotly.graph_objs as go
import geopandas as gpd
from shapely import Point
import json 
import app_utils as utils
from itables.shiny import DT
from bs4 import BeautifulSoup
import polyline
import plotly.io as pio
from pathlib import Path
from shiny.types import ImgData
import numpy as np

current_directory = os.getcwd()
data_directory = os.path.join(current_directory, 'data')
www_dir = os.path.join(current_directory, 'Frontend','www')

#Ranking Plot Preparation
pio.templates.default = "simple_white"


#SP1 File Reading


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
    ui.nav_panel("Sub-Problem 1: Cycling infrastructure suitability index","a"),
    ui.nav_panel("Sub-Problem 2: Last Mile Acessibility Index",
                ui.navset_tab(
                    ui.nav_panel("For Policy Makers",
                                 ui.page_sidebar(
                                     ui.sidebar(
                                        ui.input_select("metrics", 
                                                        "Select Metric for Comparison", 
                                                        choices=["Distance","Suitability", "Time Savings", 'Time Savings (Log)',"Weighted Score"],
                                                        selected = "Distance"),
                                        ui.input_action_button("help_button", "Definition of Metric"),
                                        ui.input_switch("exclude",
                                                        "Exclude Changi & Tuas",
                                                        value = False)
                                         ),
                                    ui.row(
                                    ui.column(7, ui.h2("Rankings by Planning Area using nearest 5 cluster method")),
                                    ui.column(5,ui.input_action_button("rationale_button", "Why 5 Clusters?"))
                                    ),
                                    ui.row(
                                        ui.column(6, ui.card(
                                                output_widget("chloropeth_map")
                                            )),
                                        ui.column(6,ui.card(
                                                output_widget("plot_planning_area_rankings")
                                            ))
                                    )
                                 )
                        
                    ),
                    ui.nav_panel("For Prospective Cyclists",
                        ui.h2("Table of path metrics for paths of individual transport stations to residential centroids"),
                        ui.page_sidebar(
                            ui.sidebar(
                                ui.input_action_button("instructions_button", "Instructions"),
                                ui.input_numeric("w1", "Weight for Distance", value=0.25, min=0, max=1, step=0.1),
                                ui.input_numeric("w2", "Weight for Suitability", value=0.25, min=0, max=1, step=0.1),
                                ui.input_numeric("w3", "Weight for Time Savings", value=0.25, min=0, max=1, step=0.1),
                                ui.input_numeric("w4", "Weight for Steepness", value=0.25, min=0, max=1, step=0.1),
                                ui.input_action_button("weight_sum_btn", "Compute Weights Sum"),
                                ui.help_text("Note: Weights should sum to 1.0"),
                                ui.output_text_verbatim("check_sum"),
                                ui.input_numeric("index_for_plot","Type here the index you wish to plot",0,min = 0,max = 1099,step = 1)
                            ),
                            ui.card(
                                ui.output_ui("centroid_mrt_metrics")
                            ),
                            ui.layout_columns(
                                ui.card(
                                    ui.value_box(
                                        title = "Route Directions",
                                        value = ui.output_text_verbatim("route_instructions"),
                                        full_screen = True
                                    )
                                ),
                                ui.card(
                                    output_widget("plot_path")
                                )
                            )
                        )
                    )
                )),
    ui.nav_panel("Sub-Problem 3: Isochrone Analysis",
                ui.h2("Distance Travellable from MRT/LRT Stations"),
                ui.page_sidebar(
                ui.sidebar(ui.input_selectize(
                    "transport_means",
                    "Select the Means of Movement (Limit to 2 Options)",
                    ["Bus", "Bicycle", "MRT", "Public Transport"],
                    multiple=True,
                    options = dict(maxItems = 2),
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
    title = ui.output_image("image",inline= True),
    bg= "#20c997"
)


def server(input, output, session):
    #General
    ##Logo
    @render.image
    def image():
        dir = Path(www_dir)
        img: ImgData = {"src": str(dir / "logo1.png"), "width": "100px"}
        return img

    #SP1 Calls

    #SP2 Calls
    #Ranking Plot
    @output
    @render_widget
    def plot_planning_area_rankings():
        df = cluster_ranking.groupby('Planning_Area').agg({input.metrics():'mean'}).reset_index()
        main_metric = input.metrics()
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
                ax=0,
                ay=-40,
                font=dict(color='red' if i < 3 else 'blue', size=12),
                arrowcolor='red' if i < 3 else 'blue'
            ))

        fig.update_layout(annotations=annotations)
        return fig

    @reactive.effect
    @reactive.event(input.rationale_button)
    async def _():
        m = ui.modal("This method involves obtaining the 5 nearest residential clusters to each MRT and obtaining path metrics through LTA OneMap and OpenrouteService.\nThe mean of the metric of interest for each planning area is then calculated by averaging that metric of all such paths within the planning area. This method is used to obtain the rankings by planning area for the metric of interest.",
                title = "What is the Nearest 5-Cluster Method?",
                easy_close=True,
                footer = None)
        ui.modal_show(m)
    
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

    @render.ui
    def centroid_mrt_metrics():
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
    
    @reactive.effect
    @reactive.event(input.instructions_button)
    async def _():
        m = ui.modal("Filter, sort, and adjust the weights to calculate the weighted score for paths connecting residential centroids to their nearest MRT/LRT station",
                title = "Instructions to compute path metrics",
                easy_close=True,
                footer = None)
        ui.modal_show(m)
    
    @reactive.calc
    @reactive.event(input.weight_sum_btn)
    def weight_sum_btn():
        input.weight_sum_btn()
        sum_weights = input.w1() + input.w2() + input.w3() + input.w4()
        return(sum_weights)
        
    
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
    
    @reactive.effect
    @reactive.event(input.help_button)    
    async def _():
        if input.metrics() == "Distance":
            m = ui.modal("""This metric describes the distance from transport stations to residential centroids,
                        and is measured by the aggregate mean of all such distances within the planning area"""
                        ,
                    title = "Definition of Metric",
                    easy_close=True,
                    footer = None)
        elif input.metrics() == "Suitability":
            m = ui.modal("""This metric quantifies the suitability of paths from transport stations to residential centroids (Obtained from ORS) and
                         is computed based on characteristics of the route and the profile of the area.
                        It is measured by the aggregate mean of all such suitability of paths within the planning area"""
                        ,
                    title = "Definition of Metric",
                    easy_close=True,
                    footer = None)
        elif input.metrics() == "Time Savings":
            m = ui.modal("""This metric quantifies the time savings of paths from transport stations to residential centroids through the formula
                         Time Savings = Time Taken by Public Transport - Time Taken by Cycling. The value is shows aggregate mean of all such time savings of paths within the planning area"""
                        ,
                    title = "Definition of Metric",
                    easy_close=True,
                    footer = None)
        else:
            m = ui.modal("""This metric is the same as the time savings variable, except that the values are the log values of the time savings.
            It is computed by the aggregate mean of all such time savings of paths within the planning area""",
            title = "Definition of Metric",
                    easy_close=True,
                    footer = None)
        ui.modal_show(m)
    
    @render_widget
    def plot_path():
        row = Centroid_MRT_df.iloc[input.index_for_plot()]
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
    
    @render.text
    def route_instructions():
        try:
            row = Centroid_MRT_df.iloc[input.index_for_plot()]
            route_instructions = row['cycle_route']['route_instructions']
            text = []
            for instruction in route_instructions:
                text.append(instruction[5] + " " + instruction[9])
            output = '\n'.join(text)
            return output
        except Exception as e:
            return ""
    
    #SP3
    def get_isochrone(name, mode, cutoff):
        variable_name = f"{mode}_isochrones"    
        df = globals()[variable_name] 
        filtered_df = df[(df['MRT.Name'] == name)]
        isochrone = filtered_df[f'isochrone_{cutoff}M'].iloc[0]
        return isochrone

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