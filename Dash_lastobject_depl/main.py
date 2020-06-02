import dash
import dash_core_components as dcc
import dash_html_components as html
from google.oauth2 import service_account
from google.cloud import bigquery
from datetime import datetime as dt
from dash.dependencies import Input, Output
import pandas as pd
import numpy as np
import pendulum
from decimal import Decimal
from plotly import graph_objects as go
import dash_auth
import json

with open('creds_dash.json') as json_data:
    creds = json.load(json_data)


VALID_USERNAME_PASSWORD_PAIRS = creds



# reading data from bigQuery
credentials = service_account.Credentials.from_service_account_file(
    'Data Warehouse LastObject-ba14bf55b88c.json')

client = bigquery.Client(credentials= credentials,project='data-warehouse-lastobject')

# reading orders table
QUERY = (
    'select DISTINCT created_at, total_price_usd, value.sku from `shopify.orders` CROSS JOIN UNNEST(line_items)  where created_at >= "2020-01-01";')
query_job = client.query(QUERY)  # API request
orders = query_job.result()  # Waits for query to finish
orders = orders.to_dataframe()
print(orders.head())

# # reading budget table
QUERY = (
    'select * from `budget.budget_2020`;')
query_job = client.query(QUERY)  # API request
budget = query_job.result()  # Waits for query to finish
budget = budget.to_dataframe()
budget['Date'] = pd.to_datetime(budget['Date'])
print(budget.info())

# orders.to_csv('orders.csv')
# budget.to_csv('budget.csv')

# orders = pd.read_csv('orders.csv')
# budget = pd.read_csv('budget.csv',parse_dates=['Date'])
# print(orders)
print(budget)

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server # the Flask app
auth = dash_auth.BasicAuth(
    app,
    VALID_USERNAME_PASSWORD_PAIRS
)

app.layout = html.Div(children=[
    html.H2(children='Perfomance Analysis App'),

    html.Div([
    	html.Div([
    dcc.DatePickerRange(
        id='date-range',
        min_date_allowed=dt(2020, 1, 1),
        max_date_allowed=dt(2020, 12, 31),
        initial_visible_month=dt(2020, 1, 1),
        start_date=dt(2020, 1, 1).date(),
        end_date=dt.now().date()
    ),],className='three columns'),

		html.Div([
			html.Button('This week', id='this-week', n_clicks=0,className='download_button'),
			],className='one columns'),

		html.Div([
			html.Button('Last week', id='last-week', n_clicks=0,className='download_button'),
			],className='one columns'),

		html.Div([
			html.Button('This month', id='this-month', n_clicks=0,className='download_button'),
			],className='one columns'),

		html.Div([
			html.Button('Last month', id='last-month', n_clicks=0,className='download_button'),
			],className='one columns'),

		html.Div([
			html.Button('This year', id='this-year', n_clicks=0,className='download_button'),
			],className='one columns'),

		html.Div([
			html.Button('Control-button-time', id='control-button-time', n_clicks=0, style = dict(display='none')),
			],className='one columns', style={'display': 'none'}),

    ],className='row'),
    html.Br(),
    html.Div([
    	html.Div([html.H5('Select Group by method: ')],className='three columns'),

		html.Div([
			html.Button('Day', id='group-by-day', n_clicks=0,className='download_button'),
			],className='one columns'),

		html.Div([
			html.Button('Week', id='group-by-week', n_clicks=0,className='download_button'),
			],className='one columns'),

		html.Div([
			html.Button('month', id='group-by-month', n_clicks=0,className='download_button'),
			],className='one columns'),

		html.Div([
			html.Button('Control-button-group', id='control-button-group', n_clicks=0, style = dict(display='none')),
			],className='one columns', style={'display': 'none'}),


    	],className='row'),
    html.Br(),
    html.Div([
    	html.Div([html.H5('Select Channel: ')],className='three columns'),
    	html.Div([
        dcc.Dropdown(
            id="channel",
            options=[{'label':name, 'value':name} for name in ['All', 'B2C_revenue', 'Wholesale_revenue', 'Distributor_revenue']],
	        placeholder="Select channel",
	        value='All',
        )],className="three columns"),


    	],className='row'),

    dcc.Graph(
        id='bar-chart',
    ),

    dcc.Graph(
        id='cum-line',
    )
])


@app.callback(
    [Output(component_id='control-button-group', component_property='n_clicks'),
    Output(component_id='bar-chart', component_property='figure'),
    Output(component_id='cum-line', component_property='figure'),],
    [Input(component_id='date-range', component_property='start_date'),
    Input(component_id='date-range', component_property='end_date'),
    Input(component_id='group-by-day', component_property='n_clicks'),
    Input(component_id='group-by-week', component_property='n_clicks'),
    Input(component_id='group-by-month', component_property='n_clicks'),
    Input(component_id='channel', component_property='value'),]
)
def update_output_div(start_date, end_date, n_clicks_group_by_day, n_clicks_group_by_week, n_clicks_group_by_month, channel):
	budget_f = budget[(budget.Date <= end_date) & (budget.Date >= start_date)]

	orders_f = orders[(orders.created_at <= end_date) & (orders.created_at >= start_date)]

	# orders_f['sku'] = orders_f.line_items.apply(lambda x: x[0]['value']['sku'])
	orders_f['sku_channel'] = orders_f['sku'].str[-1]

	orders_f = orders_f.replace({'sku_channel': {'1': 'orders B2C_revenue', '2': 'orders Wholesale_revenue', '3' : 'orders Distributor_revenue'}})
	orders_f = orders_f.drop_duplicates(subset=['created_at', 'sku_channel', 'total_price_usd'])
	
	orders_f['Date'] = orders_f['created_at'].dt.date


	print(len(orders_f))
	orders_f = orders_f.groupby(['Date','sku_channel'])[['total_price_usd']].sum().reset_index()

	metas = ['Date']

	orders_f = orders_f.set_index(['sku_channel'] + metas).unstack('sku_channel').total_price_usd.rename_axis([None], axis=1).reset_index()
	# print(orders_f)

	for col in ['orders B2C_revenue', 'orders Wholesale_revenue', 'orders Distributor_revenue']:
		if col not in orders_f.columns:
			orders_f[col] = 0
			
	budget_orders_df = pd.merge(budget_f, orders_f, on='Date', how='outer')
	budget_orders_df = budget_orders_df.fillna(0)
	budget_orders_df_cum = budget_orders_df.copy()
	budget_orders_df_cum.iloc[:, 1:] =  budget_orders_df_cum.iloc[:, 1:].cumsum()
	# print(budget_orders_df_cum)

	budget_orders_df_cum.loc[budget_orders_df_cum.Date >= dt.now(), ['orders B2C_revenue', 'orders Wholesale_revenue', 'orders Distributor_revenue']] = np.nan


	if n_clicks_group_by_day:
		if channel == 'All':
			return [1, go.Figure(
							    data=[
							        go.Bar(
							            name="B2C Budget",
							            x=budget_f["Date"],
							            y=budget_f.B2C_revenue,
							            offsetgroup=0,
									    marker_color='lightpink'
							        ),
							        go.Bar(
							            name="Wholesale Budget",
							            x=budget_f["Date"],
							            y=budget_f.Wholesale_revenue,
							            offsetgroup=0,
							            base=budget_f['B2C_revenue'],
									    marker_color='lightblue'
							        ),
							        go.Bar(
							            name="Distributor Budget",
							            x=budget_f["Date"],
							            y=budget_f.Distributor_revenue,
							            offsetgroup=0,
							            base=budget_f['B2C_revenue'] + budget_f['Wholesale_revenue'],
									    marker_color='lightgreen'
							        ),
							        go.Bar(
							            name="B2C",
							            x=orders_f['Date'],
							            y=orders_f['orders B2C_revenue'],
							            offsetgroup=1,
									    marker_color='hotpink',
									    opacity=0.5
							        ),
							        go.Bar(
							            name="Wholesale",
							            x=orders_f['Date'],
							            y=orders_f['orders Wholesale_revenue'],
							            offsetgroup=1,
							            base=orders_f['orders B2C_revenue'],
									    marker_color='rgb(50,60,255)',
									    opacity=0.5
							        ),
							        go.Bar(
							            name="Distributor",
							            x=orders_f['Date'],
							            y=orders_f['orders Distributor_revenue'],
							            offsetgroup=1,
							            base=orders_f['orders B2C_revenue'] + orders_f['orders Wholesale_revenue'],
									    marker_color='green',
									    opacity=0.5
							        )
							    ],
							    layout=go.Layout(
							        title="Revenue VS Budget",
							        yaxis_title="$ USD",
							        barmode='group',
							        height=500,
							        margin = {
	                            			't' : 50,
	                            			'b' : 50}
							    )
							),


						go.Figure(
							    data=[

							    go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum['B2C_revenue'],
						            name="B2C Budget",
								    hoverinfo='x+y',
								    mode='lines',
								    fill=None,
								    line=dict(width=2, color='lightpink'),
								    fillcolor='rgba(255,255,255,0)',
								    stackgroup='two' # define stack group
								),
								 go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum['Wholesale_revenue'],
						            name="Wholesale Budget",
								    hoverinfo='x+y',
								    mode='lines',
								    fill=None,
								    fillcolor='rgba(255,255,255,0)',
								    line=dict(width=2, color='lightblue'),
								    stackgroup='two'
								),
								 go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum['Distributor_revenue'],
						            name="Distributor Budget",
								    hoverinfo='x+y',
								    mode='lines',
								    fill=None,
								    fillcolor='rgba(255,255,255,0)',
								    line=dict(width=2, color='lightgreen'),
								    stackgroup='two'
								),
								 go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum['orders B2C_revenue'],
						            name="B2C",
								    hoverinfo='x+y',
								    mode='lines',
								    line=dict(width=0.5,
									    color='rgba(255,105,180,0.5)',),
								    stackgroup='one'
								),
								 go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum[ 'orders Wholesale_revenue'],
						            name="Wholesale",
								    hoverinfo='x+y',
								    mode='lines',
								    line=dict(width=0.5,
									    color='rgba(50,60,255,0.5)'),
								    stackgroup='one'
								),
								 go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum['orders Distributor_revenue'],
						            name="Distributor",
								    hoverinfo='x+y',
								    mode='lines',
								    line=dict(width=0.5, color='rgba(0,255,0,0.5)',),
								    stackgroup='one'
								)],
							    layout=go.Layout(
							        title="Cumulative Revenue VS Budget",
							        yaxis_title="$ USD",
							        barmode='group',
							        height=500,
							        # margin = {
	              #               			't' : 50,
	              #               			'b' : 50}
							    )

								 )]
		elif channel == 'B2C_revenue':
			return [1, go.Figure(
							    data=[
							        go.Bar(
							            name="B2C Budget",
							            x=budget_f["Date"],
							            y=budget_f.B2C_revenue,
									    marker_color='lightpink'
							        ),
							        go.Bar(
							            name="B2C",
							            x=orders_f['Date'],
							            y=orders_f['orders B2C_revenue'],
									    marker_color='hotpink',
									    opacity=0.5
							        ),
							    ],
							    layout=go.Layout(
							        title="Revenue VS Budget",
							        yaxis_title="$ USD",
							        barmode='group',
							        height=500,
							        margin = {
	                            			't' : 50,
	                            			'b' : 50}
							    )
							),


						go.Figure(
							    data=[

							    go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum['B2C_revenue'],
						            name="B2C Budget",
								    hoverinfo='x+y',
								    mode='lines',
								    fill=None,
								    line=dict(width=2, color='lightpink'),
								    fillcolor='rgba(255,255,255,0)',
								    stackgroup='two' # define stack group
								),
								 go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum['orders B2C_revenue'],
						            name="B2C",
								    hoverinfo='x+y',
								    mode='lines',
								    line=dict(width=0.5,
									    color='rgba(255,105,180,0.5)',),
								    stackgroup='one'
								),],
							    layout=go.Layout(
							        title="Cumulative Revenue VS Budget",
							        yaxis_title="$ USD",
							        barmode='group',
							        height=500,
							        # margin = {
	              #               			't' : 50,
	              #               			'b' : 50}
							    )

								 )]
		elif channel == 'Wholesale_revenue':
			return [1, go.Figure(
							    data=[
							        go.Bar(
							            name="Wholesale Budget",
							            x=budget_f["Date"],
							            y=budget_f.Wholesale_revenue,
									    marker_color='lightblue',
							        ),
							        go.Bar(
							            name="Wholesale",
							            x=orders_f['Date'],
							            y=orders_f['orders Wholesale_revenue'],
									    marker_color='rgb(50,60,255)',
									    opacity=0.5,
							        ),
							    ],
							    layout=go.Layout(
							        title="Revenue VS Budget",
							        yaxis_title="$ USD",
							        barmode='group',
							        height=500,
							        margin = {
	                            			't' : 50,
	                            			'b' : 50}
							    )
							),


						go.Figure(
							    data=[
								 go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum['Wholesale_revenue'],
						            name="Wholesale Budget",
								    hoverinfo='x+y',
								    mode='lines',
								    fill=None,
								    fillcolor='rgba(255,255,255,0)',
								    line=dict(width=2, color='lightblue'),
								    stackgroup='two'
								),
								 go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum[ 'orders Wholesale_revenue'],
						            name="Wholesale",
								    hoverinfo='x+y',
								    mode='lines',
								    line=dict(width=0.5,
									    color='rgba(50,60,255,0.5)'),
								    stackgroup='one'
								)],
							    layout=go.Layout(
							        title="Cumulative Revenue VS Budget",
							        yaxis_title="$ USD",
							        barmode='group',
							        height=500,
							        # margin = {
	              #               			't' : 50,
	              #               			'b' : 50}
							    )

								 )]
		elif channel == 'Distributor_revenue':
			return [1, go.Figure(
							    data=[
							        go.Bar(
							            name="Distributor Budget",
							            x=budget_f["Date"],
							            y=budget_f.Distributor_revenue,
									    marker_color='lightgreen'
							        ),
							        go.Bar(
							            name="Distributor",
							            x=orders_f['Date'],
							            y=orders_f['orders Distributor_revenue'],
									    marker_color='green',
									    opacity=0.5
							        ),
							    ],
							    layout=go.Layout(
							        title="Revenue VS Budget",
							        yaxis_title="$ USD",
							        barmode='group',
							        height=500,
							        margin = {
	                            			't' : 50,
	                            			'b' : 50}
							    )
							),


						go.Figure(
							    data=[
								 go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum['Distributor_revenue'],
						            name="Distributor Budget",
								    hoverinfo='x+y',
								    mode='lines',
								    fill=None,
								    fillcolor='rgba(255,255,255,0)',
								    line=dict(width=2, color='lightgreen'),
								    stackgroup='two'
								),
								 go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum['orders Distributor_revenue'],
						            name="Distributor",
								    hoverinfo='x+y',
								    mode='lines',
								    line=dict(width=0.5, color='rgba(0,255,0,0.5)',),
								    stackgroup='one'
								)],
							    layout=go.Layout(
							        title="Cumulative Revenue VS Budget",
							        yaxis_title="$ USD",
							        barmode='group',
							        height=500,
							        # margin = {
	              #               			't' : 50,
	              #               			'b' : 50}
							    )

								 )]


	elif n_clicks_group_by_week:

		budget_f['Date'] = budget_f.Date.apply(lambda x: x.strftime("%V"))

		budget_f = budget_f.groupby('Date')[['B2C_revenue', 'Wholesale_revenue', 'Distributor_revenue']].sum().reset_index()

		orders_f['Date'] = orders_f.Date.apply(lambda x: x.strftime("%V"))

		orders_f = orders_f.groupby('Date')[['orders B2C_revenue', 'orders Wholesale_revenue', 'orders Distributor_revenue']].sum().reset_index()
		# print(orders_f)


		if channel == 'All':
			return [1, go.Figure(
							    data=[
							        go.Bar(
							            name="B2C Budget",
							            x=budget_f["Date"],
							            y=budget_f.B2C_revenue,
							            offsetgroup=0,
									    marker_color='lightpink'
							        ),
							        go.Bar(
							            name="Wholesale Budget",
							            x=budget_f["Date"],
							            y=budget_f.Wholesale_revenue,
							            offsetgroup=0,
							            base=budget_f['B2C_revenue'],
									    marker_color='lightblue'
							        ),
							        go.Bar(
							            name="Distributor Budget",
							            x=budget_f["Date"],
							            y=budget_f.Distributor_revenue,
							            offsetgroup=0,
							            base=budget_f['B2C_revenue'] + budget_f['Wholesale_revenue'],
									    marker_color='lightgreen'
							        ),
							        go.Bar(
							            name="B2C",
							            x=orders_f['Date'],
							            y=orders_f['orders B2C_revenue'],
							            offsetgroup=1,
									    marker_color='hotpink',
									    opacity=0.5
							        ),
							        go.Bar(
							            name="Wholesale",
							            x=orders_f['Date'],
							            y=orders_f['orders Wholesale_revenue'],
							            offsetgroup=1,
							            base=orders_f['orders B2C_revenue'],
									    marker_color='rgb(50,60,255)',
									    opacity=0.5
							        ),
							        go.Bar(
							            name="Distributor",
							            x=orders_f['Date'],
							            y=orders_f['orders Distributor_revenue'],
							            offsetgroup=1,
							            base=orders_f['orders B2C_revenue'] + orders_f['orders Wholesale_revenue'],
									    marker_color='green',
									    opacity=0.5
							        )
							    ],
							    layout=go.Layout(
							        title="Revenue VS Budget",
							        yaxis_title="$ USD",
							        barmode='group',
							        height=500,
							        margin = {
	                            			't' : 50,
	                            			'b' : 50}
							    )
							),


						go.Figure(
							    data=[

							    go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum['B2C_revenue'],
						            name="B2C Budget",
								    hoverinfo='x+y',
								    mode='lines',
								    fill=None,
								    line=dict(width=2, color='lightpink'),
								    fillcolor='rgba(255,255,255,0)',
								    stackgroup='two' # define stack group
								),
								 go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum['Wholesale_revenue'],
						            name="Wholesale Budget",
								    hoverinfo='x+y',
								    mode='lines',
								    fill=None,
								    fillcolor='rgba(255,255,255,0)',
								    line=dict(width=2, color='lightblue'),
								    stackgroup='two'
								),
								 go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum['Distributor_revenue'],
						            name="Distributor Budget",
								    hoverinfo='x+y',
								    mode='lines',
								    fill=None,
								    fillcolor='rgba(255,255,255,0)',
								    line=dict(width=2, color='lightgreen'),
								    stackgroup='two'
								),
								 go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum['orders B2C_revenue'],
						            name="B2C",
								    hoverinfo='x+y',
								    mode='lines',
								    line=dict(width=0.5,
									    color='rgba(255,105,180,0.5)',),
								    stackgroup='one'
								),
								 go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum[ 'orders Wholesale_revenue'],
						            name="Wholesale",
								    hoverinfo='x+y',
								    mode='lines',
								    line=dict(width=0.5,
									    color='rgba(50,60,255,0.5)'),
								    stackgroup='one'
								),
								 go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum['orders Distributor_revenue'],
						            name="Distributor",
								    hoverinfo='x+y',
								    mode='lines',
								    line=dict(width=0.5, color='rgba(0,255,0,0.5)',),
								    stackgroup='one'
								)],
							    layout=go.Layout(
							        title="Cumulative Revenue VS Budget",
							        yaxis_title="$ USD",
							        barmode='group',
							        height=500,
							        # margin = {
	              #               			't' : 50,
	              #               			'b' : 50}
							    )

								 )]
		elif channel == 'B2C_revenue':
			return [1, go.Figure(
							    data=[
							        go.Bar(
							            name="B2C Budget",
							            x=budget_f["Date"],
							            y=budget_f.B2C_revenue,
									    marker_color='lightpink'
							        ),
							        go.Bar(
							            name="B2C",
							            x=orders_f['Date'],
							            y=orders_f['orders B2C_revenue'],
									    marker_color='hotpink',
									    opacity=0.5
							        ),
							    ],
							    layout=go.Layout(
							        title="Revenue VS Budget",
							        yaxis_title="$ USD",
							        barmode='group',
							        height=500,
							        margin = {
	                            			't' : 50,
	                            			'b' : 50}
							    )
							),


						go.Figure(
							    data=[

							    go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum['B2C_revenue'],
						            name="B2C Budget",
								    hoverinfo='x+y',
								    mode='lines',
								    fill=None,
								    line=dict(width=2, color='lightpink'),
								    fillcolor='rgba(255,255,255,0)',
								    stackgroup='two' # define stack group
								),
								 go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum['orders B2C_revenue'],
						            name="B2C",
								    hoverinfo='x+y',
								    mode='lines',
								    line=dict(width=0.5,
									    color='rgba(255,105,180,0.5)',),
								    stackgroup='one'
								)],
							    layout=go.Layout(
							        title="Cumulative Revenue VS Budget",
							        yaxis_title="$ USD",
							        barmode='group',
							        height=500,
							        # margin = {
	              #               			't' : 50,
	              #               			'b' : 50}
							    )

								 )]
		elif channel == 'Wholesale_revenue':
			return [1, go.Figure(
							    data=[
							        go.Bar(
							            name="Wholesale Budget",
							            x=budget_f["Date"],
							            y=budget_f.Wholesale_revenue,
									    marker_color='lightblue'
							        ),
							        go.Bar(
							            name="Wholesale",
							            x=orders_f['Date'],
							            y=orders_f['orders Wholesale_revenue'],
									    marker_color='rgb(50,60,255)',
									    opacity=0.5
							        ),
							    ],
							    layout=go.Layout(
							        title="Revenue VS Budget",
							        yaxis_title="$ USD",
							        barmode='group',
							        height=500,
							        margin = {
	                            			't' : 50,
	                            			'b' : 50}
							    )
							),


						go.Figure(
							    data=[
								 go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum['Wholesale_revenue'],
						            name="Wholesale Budget",
								    hoverinfo='x+y',
								    mode='lines',
								    fill=None,
								    fillcolor='rgba(255,255,255,0)',
								    line=dict(width=2, color='lightblue'),
								    stackgroup='two'
								),
								 go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum[ 'orders Wholesale_revenue'],
						            name="Wholesale",
								    hoverinfo='x+y',
								    mode='lines',
								    line=dict(width=0.5,
									    color='rgba(50,60,255,0.5)'),
								    stackgroup='one'
								)],
							    layout=go.Layout(
							        title="Cumulative Revenue VS Budget",
							        yaxis_title="$ USD",
							        barmode='group',
							        height=500,
							        # margin = {
	              #               			't' : 50,
	              #               			'b' : 50}
							    )

								 )]
		elif channel == 'Distributor_revenue':
			return [1, go.Figure(
							    data=[
							        go.Bar(
							            name="Distributor Budget",
							            x=budget_f["Date"],
							            y=budget_f.Distributor_revenue,
									    marker_color='lightgreen'
							        ),
							        go.Bar(
							            name="Distributor",
							            x=orders_f['Date'],
							            y=orders_f['orders Distributor_revenue'],
									    marker_color='green',
									    opacity=0.5
							        ),
							    ],
							    layout=go.Layout(
							        title="Revenue VS Budget",
							        yaxis_title="$ USD",
							        barmode='group',
							        height=500,
							        margin = {
	                            			't' : 50,
	                            			'b' : 50}
							    )
							),


						go.Figure(
							    data=[
								 go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum['Distributor_revenue'],
						            name="Distributor Budget",
								    hoverinfo='x+y',
								    mode='lines',
								    fill=None,
								    fillcolor='rgba(255,255,255,0)',
								    line=dict(width=2, color='lightgreen'),
								    stackgroup='two'
								),
								 go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum['orders Distributor_revenue'],
						            name="Distributor",
								    hoverinfo='x+y',
								    mode='lines',
								    line=dict(width=0.5, color='rgba(0,255,0,0.5)',),
								    stackgroup='one'
								)],
							    layout=go.Layout(
							        title="Cumulative Revenue VS Budget",
							        yaxis_title="$ USD",
							        barmode='group',
							        height=500,
							        # margin = {
	              #               			't' : 50,
	              #               			'b' : 50}
							    )

								 )]

	elif n_clicks_group_by_month:

		budget_f['Date'] = budget_f.Date.apply(lambda x: x.month)

		budget_f = budget_f.groupby('Date')[['B2C_revenue', 'Wholesale_revenue', 'Distributor_revenue']].sum().reset_index()

		orders_f['Date'] = orders_f.Date.apply(lambda x: x.month)

		orders_f = orders_f.groupby('Date')[['orders B2C_revenue', 'orders Wholesale_revenue', 'orders Distributor_revenue']].sum().reset_index()
		# print(orders_f)


		if channel == 'All':
			return [1, go.Figure(
							    data=[
							        go.Bar(
							            name="B2C Budget",
							            x=budget_f["Date"],
							            y=budget_f.B2C_revenue,
							            offsetgroup=0,
									    marker_color='lightpink'
							        ),
							        go.Bar(
							            name="Wholesale Budget",
							            x=budget_f["Date"],
							            y=budget_f.Wholesale_revenue,
							            offsetgroup=0,
							            base=budget_f['B2C_revenue'],
									    marker_color='lightblue'
							        ),
							        go.Bar(
							            name="Distributor Budget",
							            x=budget_f["Date"],
							            y=budget_f.Distributor_revenue,
							            offsetgroup=0,
							            base=budget_f['B2C_revenue'] + budget_f['Wholesale_revenue'],
									    marker_color='lightgreen'
							        ),
							        go.Bar(
							            name="B2C",
							            x=orders_f['Date'],
							            y=orders_f['orders B2C_revenue'],
							            offsetgroup=1,
									    marker_color='hotpink',
									    opacity=0.5
							        ),
							        go.Bar(
							            name="Wholesale",
							            x=orders_f['Date'],
							            y=orders_f['orders Wholesale_revenue'],
							            offsetgroup=1,
							            base=orders_f['orders B2C_revenue'],
									    marker_color='rgb(50,60,255)',
									    opacity=0.5
							        ),
							        go.Bar(
							            name="Distributor",
							            x=orders_f['Date'],
							            y=orders_f['orders Distributor_revenue'],
							            offsetgroup=1,
							            base=orders_f['orders B2C_revenue'] + orders_f['orders Wholesale_revenue'],
									    marker_color='green',
									    opacity=0.5
							        )
							    ],
							    layout=go.Layout(
							        title="Revenue VS Budget",
							        yaxis_title="$ USD",
							        barmode='group',
							        height=500,
							        margin = {
	                            			't' : 50,
	                            			'b' : 50}
							    )
							),


						go.Figure(
							    data=[

							    go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum['B2C_revenue'],
						            name="B2C Budget",
								    hoverinfo='x+y',
								    mode='lines',
								    fill=None,
								    line=dict(width=2, color='lightpink'),
								    fillcolor='rgba(255,255,255,0)',
								    stackgroup='two' # define stack group
								),
								 go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum['Wholesale_revenue'],
						            name="Wholesale Budget",
								    hoverinfo='x+y',
								    mode='lines',
								    fill=None,
								    fillcolor='rgba(255,255,255,0)',
								    line=dict(width=2, color='lightblue'),
								    stackgroup='two'
								),
								 go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum['Distributor_revenue'],
						            name="Distributor Budget",
								    hoverinfo='x+y',
								    mode='lines',
								    fill=None,
								    fillcolor='rgba(255,255,255,0)',
								    line=dict(width=2, color='lightgreen'),
								    stackgroup='two'
								),
								 go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum['orders B2C_revenue'],
						            name="B2C",
								    hoverinfo='x+y',
								    mode='lines',
								    line=dict(width=0.5,
									    color='rgba(255,105,180,0.5)',),
								    stackgroup='one'
								),
								 go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum[ 'orders Wholesale_revenue'],
						            name="Wholesale",
								    hoverinfo='x+y',
								    mode='lines',
								    line=dict(width=0.5,
									    color='rgba(50,60,255,0.5)'),
								    stackgroup='one'
								),
								 go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum['orders Distributor_revenue'],
						            name="Distributor",
								    hoverinfo='x+y',
								    mode='lines',
								    line=dict(width=0.5, color='rgba(0,255,0,0.5)',),
								    stackgroup='one'
								)],
							    layout=go.Layout(
							        title="Cumulative Revenue VS Budget",
							        yaxis_title="$ USD",
							        barmode='group',
							        height=500,
							        # margin = {
	              #               			't' : 50,
	              #               			'b' : 50}
							    )

								 )]
		elif channel == 'B2C_revenue':
			return [1, go.Figure(
							    data=[
							        go.Bar(
							            name="B2C Budget",
							            x=budget_f["Date"],
							            y=budget_f.B2C_revenue,
									    marker_color='lightpink'
							        ),
							        go.Bar(
							            name="B2C",
							            x=orders_f['Date'],
							            y=orders_f['orders B2C_revenue'],
									    marker_color='hotpink',
									    opacity=0.5
							        ),
							    ],
							    layout=go.Layout(
							        title="Revenue VS Budget",
							        yaxis_title="$ USD",
							        barmode='group',
							        height=500,
							        margin = {
	                            			't' : 50,
	                            			'b' : 50}
							    )
							),


						go.Figure(
							    data=[

							    go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum['B2C_revenue'],
						            name="B2C Budget",
								    hoverinfo='x+y',
								    mode='lines',
								    fill=None,
								    line=dict(width=2, color='lightpink'),
								    fillcolor='rgba(255,255,255,0)',
								    stackgroup='two' # define stack group
								),
								 go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum['orders B2C_revenue'],
						            name="B2C",
								    hoverinfo='x+y',
								    mode='lines',
								    line=dict(width=0.5,
									    color='rgba(255,105,180,0.5)',),
								    stackgroup='one'
								),],
							    layout=go.Layout(
							        title="Cumulative Revenue VS Budget",
							        yaxis_title="$ USD",
							        barmode='group',
							        height=500,
							        # margin = {
	              #               			't' : 50,
	              #               			'b' : 50}
							    )

								 )]
		elif channel == 'Wholesale_revenue':
			return [1, go.Figure(
							    data=[
							        go.Bar(
							            name="Wholesale Budget",
							            x=budget_f["Date"],
							            y=budget_f.Wholesale_revenue,
									    marker_color='lightblue'

							        ),
							        go.Bar(
							            name="Wholesale",
							            x=orders_f['Date'],
							            y=orders_f['orders Wholesale_revenue'],
									    marker_color='rgb(50,60,255)',
									    opacity=0.5
							        ),
							    ],
							    layout=go.Layout(
							        title="Revenue VS Budget",
							        yaxis_title="$ USD",
							        barmode='group',
							        height=500,
							        margin = {
	                            			't' : 50,
	                            			'b' : 50}
							    )
							),


						go.Figure(
							    data=[
								 go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum['Wholesale_revenue'],
						            name="Wholesale Budget",
								    hoverinfo='x+y',
								    mode='lines',
								    fill=None,
								    fillcolor='rgba(255,255,255,0)',
								    line=dict(width=2, color='lightblue'),
								    stackgroup='two'
								),
								 go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum[ 'orders Wholesale_revenue'],
						            name="Wholesale",
								    hoverinfo='x+y',
								    mode='lines',
								    line=dict(width=0.5,
									    color='rgba(50,60,255,0.5)'),
								    stackgroup='one'
								)],
							    layout=go.Layout(
							        title="Cumulative Revenue VS Budget",
							        yaxis_title="$ USD",
							        barmode='group',
							        height=500,
							        # margin = {
	              #               			't' : 50,
	              #               			'b' : 50}
							    )

								 )]
		elif channel == 'Distributor_revenue':
			return [1, go.Figure(
							    data=[
							        go.Bar(
							            name="Distributor Budget",
							            x=budget_f["Date"],
							            y=budget_f.Distributor_revenue,
									    marker_color='lightgreen'
							        ),
							        go.Bar(
							            name="Distributor",
							            x=orders_f['Date'],
							            y=orders_f['orders Distributor_revenue'],
									    marker_color='green',
									    opacity=0.5
							        ),
							    ],
							    layout=go.Layout(
							        title="Revenue VS Budget",
							        yaxis_title="$ USD",
							        barmode='group',
							        height=500,
							        margin = {
	                            			't' : 50,
	                            			'b' : 50}
							    )
							),


						go.Figure(
							    data=[
								 go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum['Distributor_revenue'],
						            name="Distributor Budget",
								    hoverinfo='x+y',
								    mode='lines',
								    fill=None,
								    fillcolor='rgba(255,255,255,0)',
								    line=dict(width=2, color='lightgreen'),
								    stackgroup='two'
								),
								 go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum['orders Distributor_revenue'],
						            name="Distributor",
								    hoverinfo='x+y',
								    mode='lines',
								    line=dict(width=0.5, color='rgba(0,255,0,0.5)',),
								    stackgroup='one'
								)],
							    layout=go.Layout(
							        title="Cumulative Revenue VS Budget",
							        yaxis_title="$ USD",
							        barmode='group',
							        height=500,
							        # margin = {
	              #               			't' : 50,
	              #               			'b' : 50}
							    )

								 )]
	else:
		if channel == 'All':
			return [1, go.Figure(
							    data=[
							        go.Bar(
							            name="B2C Budget",
							            x=budget_f["Date"],
							            y=budget_f.B2C_revenue,
							            offsetgroup=0,
									    marker_color='lightpink'
							        ),
							        go.Bar(
							            name="Wholesale Budget",
							            x=budget_f["Date"],
							            y=budget_f.Wholesale_revenue,
							            offsetgroup=0,
							            base=budget_f['B2C_revenue'],
									    marker_color='lightblue'
							        ),
							        go.Bar(
							            name="Distributor Budget",
							            x=budget_f["Date"],
							            y=budget_f.Distributor_revenue,
							            offsetgroup=0,
							            base=budget_f['B2C_revenue'] + budget_f['Wholesale_revenue'],
									    marker_color='lightgreen'
							        ),
							        go.Bar(
							            name="B2C",
							            x=orders_f['Date'],
							            y=orders_f['orders B2C_revenue'],
							            offsetgroup=1,
									    marker_color='hotpink',
									    opacity=0.5
							        ),
							        go.Bar(
							            name="Wholesale",
							            x=orders_f['Date'],
							            y=orders_f['orders Wholesale_revenue'],
							            offsetgroup=1,
							            base=orders_f['orders B2C_revenue'],
									    marker_color='rgb(50,60,255)',
									    opacity=0.5
							        ),
							        go.Bar(
							            name="Distributor",
							            x=orders_f['Date'],
							            y=orders_f['orders Distributor_revenue'],
							            offsetgroup=1,
							            base=orders_f['orders B2C_revenue'] + orders_f['orders Wholesale_revenue'],
									    marker_color='green',
									    opacity=0.5
							        )
							    ],
							    layout=go.Layout(
							        title="Revenue VS Budget",
							        yaxis_title="$ USD",
							        barmode='group',
							        height=500,
							        margin = {
	                            			't' : 50,
	                            			'b' : 50}
							    )
							),


						go.Figure(
							    data=[

							    go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum['B2C_revenue'],
						            name="B2C Budget",
								    hoverinfo='x+y',
								    mode='lines',
								    fill=None,
								    line=dict(width=2, color='lightpink'),
								    fillcolor='rgba(255,255,255,0)',
								    stackgroup='two' # define stack group
								),
								 go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum['Wholesale_revenue'],
						            name="Wholesale Budget",
								    hoverinfo='x+y',
								    mode='lines',
								    fill=None,
								    fillcolor='rgba(255,255,255,0)',
								    line=dict(width=2, color='lightblue'),
								    stackgroup='two'
								),
								 go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum['Distributor_revenue'],
						            name="Distributor Budget",
								    hoverinfo='x+y',
								    mode='lines',
								    fill=None,
								    fillcolor='rgba(255,255,255,0)',
								    line=dict(width=2, color='lightgreen'),
								    stackgroup='two'
								),
								 go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum['orders B2C_revenue'],
						            name="B2C",
								    hoverinfo='x+y',
								    mode='lines',
								    line=dict(width=0.5,
									    color='rgba(255,105,180,0.5)',),
								    stackgroup='one'
								),
								 go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum[ 'orders Wholesale_revenue'],
						            name="Wholesale",
								    hoverinfo='x+y',
								    mode='lines',
								    line=dict(width=0.5,
									    color='rgba(50,60,255,0.5)'),
								    stackgroup='one'
								),
								 go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum['orders Distributor_revenue'],
						            name="Distributor",
								    hoverinfo='x+y',
								    mode='lines',
								    line=dict(width=0.5, color='rgba(0,255,0,0.5)',),
								    stackgroup='one'
								)],
							    layout=go.Layout(
							        title="Cumulative Revenue VS Budget",
							        yaxis_title="$ USD",
							        barmode='group',
							        height=500,
							        # margin = {
	              #               			't' : 50,
	              #               			'b' : 50}
							    )

								 )]
		elif channel == 'B2C_revenue':
			return [1, go.Figure(
							    data=[
							        go.Bar(
							            name="B2C Budget",
							            x=budget_f["Date"],
							            y=budget_f.B2C_revenue,
									    marker_color='lightpink'
							        ),
							        go.Bar(
							            name="B2C",
							            x=orders_f['Date'],
							            y=orders_f['orders B2C_revenue'],
									    marker_color='hotpink',
									    opacity=0.5
							        ),
							    ],
							    layout=go.Layout(
							        title="Revenue VS Budget",
							        yaxis_title="$ USD",
							        barmode='group',
							        height=500,
							        margin = {
	                            			't' : 50,
	                            			'b' : 50}
							    )
							),


						go.Figure(
							    data=[

							    go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum['B2C_revenue'],
						            name="B2C Budget",
								    hoverinfo='x+y',
								    mode='lines',
								    fill=None,
								    line=dict(width=2, color='lightpink'),
								    fillcolor='rgba(255,255,255,0)',
								    stackgroup='two' # define stack group
								),
								 go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum['orders B2C_revenue'],
						            name="B2C",
								    hoverinfo='x+y',
								    mode='lines',
								    line=dict(width=0.5,
									    color='rgba(255,105,180,0.5)',),
								    stackgroup='one'
								)],
							    layout=go.Layout(
							        title="Cumulative Revenue VS Budget",
							        yaxis_title="$ USD",
							        barmode='group',
							        height=500,
							        # margin = {
	              #               			't' : 50,
	              #               			'b' : 50}
							    )

								 )]
		elif channel == 'Wholesale_revenue':
			return [1, go.Figure(
							    data=[
							        go.Bar(
							            name="Wholesale Budget",
							            x=budget_f["Date"],
							            y=budget_f.Wholesale_revenue,
									    marker_color='lightblue'
							        ),
							        go.Bar(
							            name="Wholesale",
							            x=orders_f['Date'],
							            y=orders_f['orders Wholesale_revenue'],
									    marker_color='rgb(50,60,255)',
									    opacity=0.5
							        ),
							    ],
							    layout=go.Layout(
							        title="Revenue VS Budget",
							        yaxis_title="$ USD",
							        barmode='group',
							        height=500,
							        margin = {
	                            			't' : 50,
	                            			'b' : 50}
							    )
							),


						go.Figure(
							    data=[
								 go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum['Wholesale_revenue'],
						            name="Wholesale Budget",
								    hoverinfo='x+y',
								    mode='lines',
								    fill=None,
								    fillcolor='rgba(255,255,255,0)',
								    line=dict(width=2, color='lightblue'),
								    stackgroup='two'
								),
								 go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum[ 'orders Wholesale_revenue'],
						            name="Wholesale",
								    hoverinfo='x+y',
								    mode='lines',
								    line=dict(width=0.5,
									    color='rgba(50,60,255,0.5)'),
								    stackgroup='one'
								),],
							    layout=go.Layout(
							        title="Cumulative Revenue VS Budget",
							        yaxis_title="$ USD",
							        barmode='group',
							        height=500,
							        # margin = {
	              #               			't' : 50,
	              #               			'b' : 50}
							    )

								 )]
		elif channel == 'Distributor_revenue':
			return [1, go.Figure(
							    data=[
							        go.Bar(
							            name="Distributor Budget",
							            x=budget_f["Date"],
							            y=budget_f.Distributor_revenue,
									    marker_color='lightgreen'
							        ),
							        go.Bar(
							            name="Distributor",
							            x=orders_f['Date'],
							            y=orders_f['orders Distributor_revenue'],
									    marker_color='green',
									    opacity=0.5
							        ),
							    ],
							    layout=go.Layout(
							        title="Revenue VS Budget",
							        yaxis_title="$ USD",
							        barmode='group',
							        height=500,
							        margin = {
	                            			't' : 50,
	                            			'b' : 50}
							    )
							),


						go.Figure(
							    data=[
								 go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum['Distributor_revenue'],
						            name="Distributor Budget",
								    hoverinfo='x+y',
								    mode='lines',
								    fill=None,
								    fillcolor='rgba(255,255,255,0)',
								    line=dict(width=2, color='lightgreen'),
								    stackgroup='two'
								),
								 go.Scatter(
								    x=budget_orders_df_cum.Date, y=budget_orders_df_cum['orders Distributor_revenue'],
						            name="Distributor",
								    hoverinfo='x+y',
								    mode='lines',
								    line=dict(width=0.5, color='rgba(0,255,0,0.5)',),
								    stackgroup='one'
								)],
							    layout=go.Layout(
							        title="Cumulative Revenue VS Budget",
							        yaxis_title="$ USD",
							        barmode='group',
							        height=500,
							        # margin = {
	              #               			't' : 50,
	              #               			'b' : 50}
							    )

								 )]


@app.callback(
    [Output(component_id='control-button-time', component_property='n_clicks'),
    Output(component_id='date-range', component_property='start_date'),
    Output(component_id='date-range', component_property='end_date')],
    [Input(component_id='this-week', component_property='n_clicks'),
    Input(component_id='last-week', component_property='n_clicks'),
    Input(component_id='this-month', component_property='n_clicks'),
    Input(component_id='last-month', component_property='n_clicks'),
    Input(component_id='this-year', component_property='n_clicks'),]
)
def update_output_div(n_clicks_this_week, n_clicks_last_week, n_clicks_this_month, n_clicks_last_month, n_clicks_this_year):
	if n_clicks_this_week:
		today = pendulum.now()
		start = today.start_of('week')
		end = today.end_of('week')
		return [1, start.date(), end.date()]
	elif n_clicks_last_week:
		today = pendulum.now()
		start = today.subtract(weeks=1).start_of('week')
		end = today.subtract(weeks=1).end_of('week')
		return [1, start.date(), end.date()]
	elif n_clicks_this_month:
		today = pendulum.now()
		start = today.start_of('month')
		end = today.end_of('month')
		return [1, start.date(), end.date()]
	elif n_clicks_last_month:
		today = pendulum.now()
		start = today.subtract(months=1).start_of('month')
		end = today.subtract(months=1).end_of('month')
		return [1, start.date(), end.date()]
	elif n_clicks_this_year:
		today = pendulum.now()
		start = today.start_of('year')
		end = today.end_of('year')
		return [1, start.date(), end.date()]

	else:
		return [1, dt(2020, 1, 1).date(), dt.now().date()]

@app.callback(
    [Output(component_id='this-week', component_property='n_clicks'),
    Output(component_id='last-week', component_property='n_clicks'),
    Output(component_id='this-month', component_property='n_clicks'),
    Output(component_id='last-month', component_property='n_clicks'),
    Output(component_id='this-year', component_property='n_clicks'),],
    [Input(component_id='control-button-time', component_property='n_clicks'),]

)
def update_output_div(n_clicks):
	if n_clicks:
		return [0, 0, 0, 0, 0]
	else:
		return [0, 0, 0, 0, 0]
		

@app.callback(
    [Output(component_id='group-by-day', component_property='n_clicks'),
    Output(component_id='group-by-week', component_property='n_clicks'),
    Output(component_id='group-by-month', component_property='n_clicks'),],
    [Input(component_id='control-button-group', component_property='n_clicks'),]

)
def update_output_div(n_clicks):
	if n_clicks:
		return [0, 0, 0]
	else:
		return [0, 0, 0]


if __name__ == '__main__':
    app.run_server(debug=False) #, use_reloader=False