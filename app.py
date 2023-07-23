import dash
from dash import dash_table
from dash import dcc
from dash import html
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate

import plotly.graph_objs as go
import plotly.express as px
import geopandas as gpd
import pandas as pd
from datetime import datetime

# Hoja de estilos
external_stylesheets = ['assets/style.css']

# Función para crear las visualizaciones
def update_counts(colnect, data_paises, map_df):
    monedas_pais = colnect.groupby(['País'])['Nombre'].agg('count').reset_index().sort_values('Nombre', ascending=False).rename(columns={'Nombre': 'Cantidad'})
    monedas_pais = monedas_pais.merge(data_paises, on='País', how='outer')

    # Cruce de la data de monedas contra el shape
    map_df_m = map_df.merge(monedas_pais, on=['COUNTRY', 'FID'], how='left')
    map_df_m['Cantidad'] = map_df_m['Cantidad'].fillna(0)

    # Conteo total de monedas en la colección
    total_col = colnect['Fecha emisión'].count()

    # Conteo total de monedas de países actuales
    total_monedas = map_df_m['Cantidad'].sum()

    # Selección del país con más monedas
    max_cantidad = map_df_m['Cantidad'].max()
    id_max = map_df_m['Cantidad'].idxmax()
    pais_max = map_df_m.loc[id_max]['País']

    # Lista de países actuales
    actuales = map_df_m['País'].unique().tolist()

    # Conteo de monedas por paises inexistentes
    antiguos = colnect[~colnect['País'].isin(actuales)]
    antiguos_count = antiguos.groupby('País')['Nombre'].count().reset_index(name='count')
    antiguos_count = antiguos_count.sort_values(by='count', ascending=False)

    # Devolución de resultados
    return actuales, antiguos_count, total_monedas, max_cantidad, id_max, pais_max, map_df_m

# Función para crear el mapa
def create_map(map_df_m, text):
    trace = go.Choropleth(
        geojson=map_df_m.__geo_interface__,
        locations=map_df_m.index,
        z=map_df_m['Cantidad'],
        text=text,
        hovertemplate='%{text}',
        colorscale=colorscale,
        autocolorscale=False,
        reversescale=True,
        marker_line_color='white',
        marker_line_width=0,
        colorbar_title='Cantidad de monedas',
        showscale=False,
        name='',
        hoverlabel=dict(
            bgcolor='#f0f7fa',  # Estableciendo el fondo blanco
            font=dict(color='black')  # Estableciendo el color de letra en negro
        )
    )

    layout = go.Layout(
        title_x=0.5,
        title_y=0.9,
        width=1000,
        height=500,
        margin=dict(l=1, r=1, t=0, b=0),
        mapbox_style='open-street-map',
        mapbox_zoom=10,
        mapbox_center={'lat': 0, 'lon': 0,
                    },
    )

    return trace, layout

#  Función para crear el histograma
def create_histo(colnect):
    histo = px.histogram(colnect, x='Fecha emisión', nbins=500)
    histo.update_traces(showlegend=False)
    histo.update_layout(
        title={'text': "Monedas por año de emisión", 'x': 0.5},
        xaxis_title="Año",
        yaxis_title="Monedas",
        plot_bgcolor="white"
    )

    return histo      


# Carga de la data de la colección
colnect = pd.read_excel('Coleccion.xlsx', sheet_name='Monedas')
colnect['Fecha emisión'] = colnect['Fecha emisión'].str.slice(0, 4).astype(int)

# Carga del shape file
map_df = gpd.read_file('World_Countries.zip')

# Lectura data de países
data_paises = pd.read_csv('dataset_paises_all.csv', sep=',')

# Conteo de monedas por país
monedas_pais = colnect.groupby(['País'])['Nombre'].agg('count').reset_index(
).sort_values('Nombre', ascending=False).rename(columns={'Nombre': 'Cantidad'})

# Carga inicial de datos en la visualizacion
data_global = update_counts(colnect, data_paises, map_df)

map_df_m = data_global[6]
total_col = colnect['Fecha emisión'].count()
total_monedas = data_global[2]
max_cantidad = data_global[3]
id_max = data_global[4]
pais_max = data_global[5]
actuales = data_global[0]
antiguos = colnect[~colnect['País'].isin(actuales)]
antiguos_count = data_global[1]
#antiguos_count.rename(columns={'País': 'País o territorio', 'count': 'Cantidad'}, inplace=True)
#print(antiguos_count.head())

# Creación del mapa
colorscale = [
    [0, 'rgb(0,0,255)'],
    [1, 'rgb(255,255,255)']
]

text = ['<b>País:</b> {} <br><b>Cantidad:</b> {:.0f}'.format(pais, cantidad) for pais, cantidad in zip(map_df_m['País'], map_df_m['Cantidad'])]

trace, layout = create_map(map_df_m, text)
fig = go.Figure(data=[trace], layout=layout)

# Creación del histograma
histo = create_histo(colnect)

# Define la fecha actual
now = datetime.now()
date_string = now.strftime("%d/%m/%Y")

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div([

    html.H1(className = "titulo-monedas", children = f'¿Cómo va mi colección de monedas?'),
    html.H3(f'{date_string}'),
    html.H2(f'Total de monedas en la colección: {int(total_col)}'),
    html.H3(f'Seleccione el rango temporal (en años) del que quiere ver más detalles:'),

    html.Div([
        dcc.RangeSlider(
            id='year-slider',
            min=int(colnect['Fecha emisión'].min()),
            max=int(colnect['Fecha emisión'].max()),
            value=[int(colnect['Fecha emisión'].min()),
                   int(colnect['Fecha emisión'].max())],
            marks={str(year): str(year) for year in range(int(
                colnect['Fecha emisión'].min()), int(colnect['Fecha emisión'].max())+1, 100)}
        )
    ], className='text-center'),

    html.Div([
        dcc.Graph(id='histogram', figure=histo)
    ], className='text-center'),

    html.H2(id='label_1', children=f'Total de monedas de países actuales: {int(total_monedas)}'),
    html.H4(id='label_2', children=f'El país del que más tengo monedas es: {pais_max} con {int(max_cantidad)} monedas'),
    html.H3(f'Distribución de monedas por país'),

    html.Div([
        dcc.Graph(id='map', figure=fig)
    ], className='map-style'),

    html.H2(f'Monedas de territorios que no son países actuales'),

    dash_table.DataTable(
        id='tabla',
        data=antiguos_count.to_dict('records'),
        columns=[{'id': i, 'name': i} for i in antiguos_count.columns]
    )

], style={'margin': 'auto', 'width': '80%'})


# Actualización del histograma
@app.callback(
    dash.dependencies.Output('histogram', 'figure'),
    [dash.dependencies.Input('year-slider', 'value')]
)
def update_histogram(year_range):

    colnect_filter = colnect[(colnect['Fecha emisión'].astype(int) >= year_range[0]) & (colnect['Fecha emisión'].astype(int) <= year_range[1])]

    histo = create_histo(colnect_filter)

    return histo

# Actualización del mapa
@app.callback(
    dash.dependencies.Output('map', 'figure'),
    [dash.dependencies.Input('year-slider', 'value')]
)
def update_map(year_range):

    colnect_filter = colnect[(colnect['Fecha emisión'].astype(int) >= year_range[0]) & (colnect['Fecha emisión'].astype(int) <= year_range[1])]

    map_df_m_filter = update_counts(colnect_filter, data_paises, map_df)[6]

    text = ['<b>País:</b> {} <br><b>Cantidad:</b> {:.0f}'.format(pais, cantidad) for pais, cantidad in zip(map_df_m_filter['País'], map_df_m_filter['Cantidad'])]

    trace, layout = create_map(map_df_m_filter, text)
    map_fig = go.Figure(data=[trace], layout=layout)

    return map_fig

# Actualización de la tabla
@app.callback(
    dash.dependencies.Output('tabla', 'data'),
    [dash.dependencies.Input('year-slider', 'value')]
)
def update_table(year_range):

    colnect_filter = colnect[(colnect['Fecha emisión'].astype(int) >= year_range[0]) & (colnect['Fecha emisión'].astype(int) <= year_range[1])]

    tabla = update_counts(colnect_filter, data_paises, map_df)[1].to_dict('records')
    return tabla

# Actualización de los labels
@app.callback(
    [dash.dependencies.Output('label_1', 'children'),
     dash.dependencies.Output('label_2', 'children')],
    [dash.dependencies.Input('year-slider', 'value')]
)
def update_labels(year_range):

    colnect_filter = colnect[(colnect['Fecha emisión'].astype(int) >= year_range[0]) & (colnect['Fecha emisión'].astype(int) <= year_range[1])]

    resultados = update_counts(colnect_filter, data_paises, map_df)

    total_monedas_text = f'Total de monedas de países actuales: {int(resultados[2])}'
    actuales_monedas_text = f'El país del que más tengo monedas es: {resultados[5]} con {int(resultados[3])} monedas'

    return total_monedas_text, actuales_monedas_text

if __name__ == '__main__':
    app.run_server(debug=True)
