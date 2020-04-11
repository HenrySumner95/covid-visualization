import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
from bokeh.plotting import figure, output_file, show
from bokeh.models import ColumnDataSource, LabelSet, Label, NumeralTickFormatter, CustomJS, Slider
from bokeh.layouts import column
from bokeh.embed import components

df = pd.read_csv("diseases.csv")

source = 'https://en.wikipedia.org/wiki/2019%E2%80%9320_coronavirus_pandemic_by_country_and_territory#Confirmed_cases'

website_url = (requests
               .get('https://en.wikipedia.org/wiki/2019%E2%80%9320_coronavirus_pandemic_by_country_and_territory#Confirmed_cases')
               .text)
soup = BeautifulSoup(website_url, 'lxml')
My_table = soup.find('table', {'class' : 'wikitable'})
items = My_table.findAll('b')

cases_dict = {}

#Keep the second and third items, cases and deaths respectively
for item in items:
    #determine where b tag starts and ends in the string
    start = str(item).find("<b>") + len("<b>")
    stop = str(item).find("</b>")
    if items.index(item) == 1:
        item = str(item)[start:stop]
        item = item.replace(",", "")
        item = int(item)
        cases_dict.update({"cases" : [item]})
    elif items.index(item) == 2:
        item = str(item)[start:stop]
        item = item.replace(",", "")
        item = int(item)
        cases_dict.update({"deaths" : [item]})
    else:
        continue
        
#Add scraped info to df 
cases_dict.update({"disease" : ["Covid-19"],
                   "source"  : [source],
                   "type"    : ["Coronavirus"]})
           
df = df.append(pd.DataFrame(cases_dict))

df = df[["disease", "deaths", "cases", "type"]]

color_dict = {"Influenza"   : "#ff0052",
              "Coronavirus" : "#ffff00",
              "Ebolavirus"  : "#009ce6"}
              
df["colour"] = df["type"].map(color_dict)
df['mortality'] = df['deaths'] / df['cases']
df['size'] = df['deaths'] / 5000
df['size'] = np.clip(df['size'], a_min = 1, a_max = 200)

circle_source = ColumnDataSource(data = df)

#Define custom HTML for tooltips
TOOLTIPS = """
    <style>
        .bk-tooltip{
            background-color:#383838 !important
        }
    </style>
    <div style = "background-color:#383838 !important; color:#eeeeee !important">
        <p><b>Virus</b>: @disease</p>
        <p><b>Type</b>: @type</p>
        <p><b>Deaths</b>: @deaths{0,0}</p>
        <p><b>Cases</b>: @cases{0,0}</p>
        <p><b>Mortality</b>: @mortality{0,0.00%}</p>
    </div>
"""

p = figure(plot_width = 800, plot_height = 600,
           x_axis_type = "log", y_axis_label = "Mortality Rate",
           x_axis_label = "Number of Cases (logarithmic scale)",
          tools = "", toolbar_location = None, tooltips = TOOLTIPS)
          
p.circle(x = "cases", y = "mortality", size = "size",
         source = circle_source, alpha = 0.5, color = "colour",
         line_color = "colour", hover_fill_alpha = 0.7,
         hover_fill_color = "colour", hover_line_color = "colour",
         legend = "type"
         )
         
remaining_labels = df[df['disease'].isin(['Seasonal Influenza',
                                          'Covid-19']) == False]
remaining_labels['disease'] = np.where(remaining_labels['disease'].str.contains('Seasonal'),
                                       "Seasonal flu", remaining_labels['disease'])
                                       
remaining_labels['xoffset'] = np.where(remaining_labels['disease'].str.contains('Swine'),
                                       -110, 0)
remaining_labels['yoffset'] = np.where(remaining_labels['disease'].str.contains('Swine'),
                                       30,
                                       np.where(remaining_labels['disease'].str.contains('Seasonal'), 25, 0))
                                       
remaining_labels = ColumnDataSource(data = remaining_labels)

labels = LabelSet(x = 'cases', y = 'mortality', text = 'disease', level = 'glyph',
                  x_offset = "xoffset", y_offset = "yoffset",
                  source = remaining_labels, render_mode = 'canvas',
                  text_color = "#eeeeee", text_font_size = "8pt")

seasonal_flu = Label(x = df[df['disease'] == 'Seasonal Influenza']['cases'].values[0],
                    y = df[df['disease'] == 'Seasonal Influenza']['mortality'].values[0],
                   text = "Seasonal Flu",
                    x_offset = -30, y_offset = -6, text_color = "#eeeeee", text_font_size = "8pt")

covid_19 = Label(x = df[df['disease'] == 'Covid-19']['cases'].values[0],
                    y = df[df['disease'] == 'Covid-19']['mortality'].values[0],
                   text = "Covid-19",
                    x_offset = -20, y_offset = 10, text_color = "#eeeeee", text_font_size = "11pt",
                text_font_style = "bold")

#Must use a data label for bubble size label as there's no functionality for custom legends
BubbleSize = Label(x = 100000000,
                    y = 0.425,
                   text = "Bubble size = Number of deaths",
                    x_offset = -60, y_offset = 0, text_color = "#eeeeee", text_font_size = "10pt",
                text_font_style = "bold")
                
#Create slider object to control number of cases
cases_slider = Slider(start=df[df["disease"] == "Covid-19"]["cases"].values[0],
                      end=100000000, value=1, step=1, title="Cases", format = "0,0")

#Define custom javascript callback to change data when user interacts with slider
callback = CustomJS(args=dict(source=circle_source, cases = cases_slider),
                    code="""
    const data = source.data;
    const A = cases.value;
    const mort = data.mortality
    const deaths = data.deaths
    const disease = data.disease
    const new_cases = data.cases
    const size = data.size
    for (var i = 0; i < disease.length; i++) {
        if (disease[i] == "Covid-19") {
            deaths[i] = mort[i]*A
            new_cases[i] = A
            size[i] = (mort[i]*A) / 5000
        }
    }
    source.change.emit();
""")

cases_slider.js_on_change('value', callback)

p.yaxis.formatter = NumeralTickFormatter(format="0%")
p.xaxis.formatter = NumeralTickFormatter(format="0,0")
p.background_fill_color = '#383838'
p.border_fill_color = '#383838'
p.xgrid.grid_line_color = '#464646'
p.ygrid.grid_line_color = '#464646'
p.xaxis.major_label_text_color = "#eeeeee"
p.yaxis.major_label_text_color = "#eeeeee"
p.yaxis.axis_label_text_color = "#eeeeee"
p.xaxis.axis_label_text_color = "#eeeeee"
p.xaxis.axis_line_color = "#eeeeee"
p.yaxis.axis_line_color = "#eeeeee"
p.xaxis.major_tick_line_color = "#eeeeee"
p.yaxis.major_tick_line_color = "#eeeeee"
p.xaxis.minor_tick_line_color = "#eeeeee"
p.yaxis.minor_tick_line_color = "#eeeeee"
p.add_layout(labels)
p.add_layout(seasonal_flu)
p.add_layout(covid_19)
p.add_layout(BubbleSize)      

                                       
p.legend.location = "top_right"
p.legend.background_fill_alpha = 0.0
p.legend.label_text_color = "#eeeeee"                                       
                                       
# output_file("covidvis.html", title = "something")

layout = column(
    p,
    cases_slider,
)

script, div = components(layout)

# show(layout)

print("script: ", script)
print("div:", div)

html_template = r"""

<!DOCTYPE html>
<html lang="en">
    <head>
        <link rel="stylesheet" href="styles.css">
        <link href="https://fonts.googleapis.com/css2?family=Roboto+Condensed:wght@300&display=swap" rel="stylesheet"></head>
        <meta charset="utf-8">
        <title>Bokeh Scatter Plots</title>

        <script src="https://cdn.bokeh.org/bokeh/release/bokeh-2.0.1.min.js"
        crossorigin="anonymous"></script>
		<script src="https://cdn.bokeh.org/bokeh/release/bokeh-widgets-2.0.1.min.js"
				crossorigin="anonymous"></script>
		<script src="https://cdn.bokeh.org/bokeh/release/bokeh-tables-2.0.1.min.js"
        crossorigin="anonymous"></script>

        {0}

    </head>
    <body>
    <div><p class = "title">Why Covid-19 is different</p></div>
        {1}
    </body>
</html>""".format(script, div)

# Write HTML String to file.html
with open("covidvis.html", "w") as file:
    file.write(html_template)