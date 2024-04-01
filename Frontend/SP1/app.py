from shiny import App, reactive, render, ui
from shinywidgets import output_widget, register_widget #render_plotly,render_widget 
import plotly.graph_objects as go
import os
import json
import shapely
import geopandas as gpd
import pandas as pd
from myUtils import prepData, createMap

# current_directory = os.getcwd()
# data_directory = os.path.join(current_directory, 'data') #../../
# file_path1 = os.path.join(data_directory, 'subZoneScore.csv')
# subZoneScore = pd.read_csv(file_path1)
# subZoneScore['geometry'] = subZoneScore['geometry'].apply(shapely.from_wkt)
# subZoneScore = gpd.GeoDataFrame(subZoneScore)

city_centers = {
    "London": (103.9, 1.38),
    "Paris": (104, 1.40),
    "New York": (103.8, 1.36)
}
subZoneScore, parkConnector = prepData()


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
                    "toggle", "Show/Hide data", {"Earthquakes": "Earthquakes (blue)", "Volcanoes": "Volcanoes (red)"},
                    selected = ["Earthquakes", "Volcanoes"]
                ),
            ),
            ui.input_select(
                "center",
                "Center",
                choices=list(city_centers.keys())
            ),
            # Set step to 5 for intervals of 5 minutes
            ui.input_slider(
                "n_min",
                "Select Maximum Time (in minutes)",
                min=10, max=60, value=5, step=5
            )
        )
    ),
    output_widget("plot")
)



def server(input, output, session):


    #@output
    #@render_widget
    
    @render_plotly
    def plot():
        map = createMap(subZoneScore, parkConnector)
        register_widget("map", map)

    @reactive.Effect
    def _():
        showE = 'Earthquakes' in input.toggle()
        showV = 'Volcanoes' in input.toggle()
        map.data[0].visible = showE
        map.data[1].visible = showV


        # fig = go.Figure(go.Choroplethmapbox(
        #            geojson=json.loads(subZoneScore.geometry.to_json()),
        #            locations=subZoneScore.index,
        #            colorscale="mint",
        #            z=subZoneScore['score'],
        #            text = subZoneScore['DESCRIPTION'],
        #            hovertemplate="%{text}<br><br><span style = \"font-size: 1.2em;\"><b>Overall Score: </b>: %{z}</span>"
        #            ))
        # fig.update_layout(
        #     margin ={'l':0,'t':0,'b':0,'r':0},
        #     mapbox = {
        #         'center': {'lon': 103.9, 'lat': 1.38},
        #         'style': "open-street-map",
        #         'center': {'lon': 103.9, 'lat': 1.38},
        #         'zoom': 10})
        # return fig

# @reactive.effect
# def _():
#     plot.widget.center = city_centers[input.center()]

app = App(app_ui, server)
# if __name__ == "__main__":
#     app.run()