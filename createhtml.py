import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
from bokeh.plotting import figure, output_file, show
from bokeh.models import ColumnDataSource, LabelSet, Label, NumeralTickFormatter, CustomJS, Slider
from bokeh.layouts import column
from bokeh.embed import components

df = pd.read_csv("diseases.csv")

source = 'https://en.wikipedia.org/wiki/COVID-19_pandemic_by_country_and_territory#Confirmed_cases'

website_url = (requests
               .get(source)
               .text)
soup = BeautifulSoup(website_url, 'lxml')
My_table = soup.find('table', {'class' : 'wikitable'})
# items = My_table.findAll('b')

items = My_table.findAll('th')

cases_dict = {}

for item in items:
    if items.index(item) == 7:
        value = str(item.get_text(strip = True))
        value = value.replace(",", "")
        value = int(value)
        cases_dict.update({"cases" : [value]})
    elif items.index(item) == 8:
        value = str(item.get_text(strip = True))
        value = value.replace(",", "")
        value = int(value)
        cases_dict.update({"deaths" : [value]})
    else:
        continue

#Keep the second and third items, cases and deaths respectively
# for item in items:
#     #determine where b tag starts and ends in the string
#     start = str(item).find("<b>") + len("<b>")
#     stop = str(item).find("</b>")
#     if items.index(item) == 1:
#         item = str(item)[start:stop]
#         item = item.replace(",", "")
#         item = int(item)
#         cases_dict.update({"cases" : [item]})
#     elif items.index(item) == 2:
#         item = str(item)[start:stop]
#         item = item.replace(",", "")
#         item = int(item)
#         cases_dict.update({"deaths" : [item]})
#     else:
#         continue
        
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
                      end=100000000, value=df[df["disease"] == "Covid-19"]["cases"].values[0]
                      , step=1, title="Cases", format = "0,0")

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

html_template = r"""

<!DOCTYPE html>
<html lang="en">
    <head>
        <meta property="og:image" content="https://s3.eu-west-2.amazonaws.com/henrysumner.com/img/graph.PNG" />
        <meta property="og:type" content="website"/>
        <meta property="og:title" content="Why Covid-19 is different" />
        <meta property="og:url" content="http://henrysumner.com/covid_visualisation/covidvis.html"/>
        <meta property="og:description" content="Data visualization showing the reason why Covid-19 is not like other viruses" />
        <link rel="stylesheet" href="styles.css">
        <link href="https://fonts.googleapis.com/css2?family=Roboto+Condensed:wght@300&display=swap" rel="stylesheet"></head>
        <meta charset="utf-8">
        <title>Why Covid-19 is different</title>

        <script src="https://cdn.bokeh.org/bokeh/release/bokeh-2.0.1.min.js"
        crossorigin="anonymous"></script>
		<script src="https://cdn.bokeh.org/bokeh/release/bokeh-widgets-2.0.1.min.js"
				crossorigin="anonymous"></script>
		<script src="https://cdn.bokeh.org/bokeh/release/bokeh-tables-2.0.1.min.js"
        crossorigin="anonymous"></script>

        {0}

    </head>
    <body>
    <div class="navbar">
        <a href="https://github.com/HenrySumner95/covid-visualization"><img src="C:\Users\ashto\work\portfolio_site\img\github white.png" width = "25px" hspace = "20"></a>
    </div>
    <div><p class = "title">Why Covid-19 is different</p>
         <p class = "little_title">Number of Cases vs Mortality for recent high-profile viruses</p></div>
    <div class = "container">
        {1}
    <div style = "padding-left : 50px; padding-right : 100px">
        <p align = "center" class = "explanation">Use the slider at the bottom to increase the number of Covid-19 cases on the graph.</p>
        <p align = "center" class = "explanation">The predicted number of deaths from the disease is a simple calculation:</p>
        <p align = "center" class = "calculation">Mortality(%) * Number of cases</p>
        <br>
        <p align = "center" class = "explanation">Covid-19 has not yet <b style = "color : #ff0052">infected</b> as many people as swine flu or seasonal flu</p>
        <p align = "center" class = "explanation">It is not as <b style = "color : #ff0052">deadly</b> as Ebola, Bird Flu, or SARS</p>
        <p align = "center" class = "explanation">But it is both <b style = "color : #ff0052">deadly</b> enough and <b style = "color : #ff0052">infectious</b> enough to potentially be the worst pandemic since Spanish Flu, which killed 50 million people. <p align = "center" class = "explanation" style = "font-size: 1em">(The bubble wouldn't even fit on my graph)</p></p>        
        <p align = "center" class = "explanation" style = "font-size : 2em"><b style = "color : #ff0052">Please</b> stay inside.</p>
    </div>
    </div>
    <div>
    <p class = "title">
    Sources
    </p>
    <p class = "explanation">Current Covid 19 cases and deaths:</p> <a href = "https://en.wikipedia.org/wiki/2019%E2%80%9320_coronavirus_pandemic_by_country_and_territory#" class = "explanation"> https://en.wikipedia.org/wiki/2019%E2%80%9320_coronavirus_pandemic_by_country_and_territory# </a> <p class = "explanation">(Compiled from WHO Daily situation report)</p>
    <p class = "explanation">Bird Flu (H5N1):</p> <a href = "https://www.who.int/influenza/human_animal_interface/2020_01_20_tableH5N1.pdf?ua=1" class = "explanation">https://www.who.int/influenza/human_animal_interface/2020_01_20_tableH5N1.pdf?ua=1</a>
    <p class = "explanation">SARS:</p> <a href = "https://www.nhs.uk/conditions/sars/" class = "explanation">https://www.nhs.uk/conditions/sars/</a>
    <p class = "explanation">MERS:</p> <a href = "https://www.who.int/emergencies/mers-cov/en/" class = "explanation">https://www.who.int/emergencies/mers-cov/en/</a>
    <p class = "explanation">Swine Flu:</p> <a href = "https://www.thelancet.com/journals/laninf/article/PIIS1473-3099(12)70121-4/fulltext" class = "explanation">https://www.thelancet.com/journals/laninf/article/PIIS1473-3099(12)70121-4/fulltext</a>
    <p class = "explanation">Ebola:</p> <a href = "https://apps.who.int/gho/data/node.ebola-sitrep.quick-downloads?lang=en" class = "explanation">https://apps.who.int/gho/data/node.ebola-sitrep.quick-downloads?lang=en</a>
    <p class = "explanation">Seasonal influenza: </p> <a href = "https://www.who.int/influenza/surveillance_monitoring/bod/FAQsInfluenzaMortalityEstimate.pdf?ua=1" class = "explanation">https://www.who.int/influenza/surveillance_monitoring/bod/FAQsInfluenzaMortalityEstimate.pdf?ua=1</a> <p class = "explanation"> | </p> <a href = "https://fullfact.org/health/coronavirus-compare-influenza/" class = "explanation">https://fullfact.org/health/coronavirus-compare-influenza/</a> <p class = "explanation">(Two sources)</p>
    </div>
    </body>
</html>""".format(script, div)

# Write HTML String to file.html
with open("covidvis.html", "w") as file:
    file.write(html_template)