"""
HKNewsWatch App
"""
from worker import conn
import uuid
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import wordcloud
import pandas as pd
import numpy as np
from rq import Queue
# from time import  time
import app_items as items
from app_functions import prepare_data

#wordcloud parameters
font_path = 'assets/AquaKana.ttc'

#Wordcloud image path
image_directory = 'assets/'

#Initialize app items
DROPDOWN_ITEM = items.create_dropdown(component_id="keyword", item_file='default_keywords.txt')
INPUT_ITEM = items.create_input(component_id='keyword')

#Initialize app
app = dash.Dash(__name__)
server = app.server

app.layout = html.Div(
    [html.Div([
        html.H1('媒體監察', style={'textAlign': 'center'}),
        html.Label('藉搜索關鍵字附近較常出現的詞語，以了解本港各媒體對各政策、人物、事件的觀點取向或對社會上不同族群的刻板印象。',
                   style={'textAlign': 'center'}),
        html.Hr()
        ],
              className="container u-full-width"),

     html.Div([
         html.Div([
             html.Div([
                 html.H6('報章'),
                 items.create_checklist(filename="newssource_chinese_trans.json",
                                        component_id="sourcechoice")],
                      className="eight columns"),

             html.Div([
                 html.H6('關鍵字'),
                 dcc.RadioItems(id='search-method',
                                options=[
                                    {'label': '選擇關鍵字', 'value': 'choice'},
                                    {'label': '輸入關鍵字', 'value': 'input'}],
                                value='choice',
                                labelStyle={'display': 'inline-block',
                                            'width':'50%'},
                                inputStyle={'min-height':'1.2rem',
                                            'min-width':'1.2rem'}),
                 html.Div([DROPDOWN_ITEM],
                          id='search-grid',
                          style={'margin-bottom':'10px'})
                 ],
                      className="four columns")],
                  className="row"),

         html.Div([
             html.Div(items.create_button(message='準備中...',
                                          button_type="button",
                                          component_id="button"),
                      id='button-div',
                      className="row",
                      style={"textAlign":"center"}),
             html.Div('INITIALIZE',
                      id='signal', style={'display':'none'}),
             html.Div(id='job-id', style={'display': 'none'}),
             dcc.Interval(id='update-interval',
                          interval=60*60*5000, # in milliseconds
                          n_intervals=0)
             ],
                  className='row')
         ],
              className="container u-full-width"),

     html.Div([
         html.Div([
             html.Div(id='output-df',
                      className='six columns u-full-width',
                      style={"border":'1px solid White'}),
             html.Div([
                 html.Img(id='wordcloud', className='u-full-width')],
                      className='six columns')],
                  className="row")],
              className="container u-full-width")
     # html.Div(
     #     [html.Div(id='time-log')],
     #     className="container")
     ],
    className='container')

@app.callback(
    Output('search-grid', 'children'),
    [Input('search-method','value')])
def update_search_method(search_method):
    """
    Update search method depending on user choices
    """
    if search_method == 'choice':
        return DROPDOWN_ITEM
    return INPUT_ITEM

@app.callback(
    Output('job-id', 'children'),
    [Input('button', 'n_clicks')],
    state=[State('keyword', 'value'),
           State('sourcechoice', 'values')])
def submit_query(n_click, keyword, sourcechoice):
    """
    Submit search query to work dyno and retrun speific job ID.
    """
    q = Queue(connection=conn)
    job_id = str(uuid.uuid4())
    q.enqueue_call(func=prepare_data,
                   args=(keyword, sourcechoice),
                   timeout='3m',
                   job_id=job_id)
    print('Job Submiited')

    return job_id

@app.callback(
    Output('update-interval', 'interval'),
    [Input('job-id', 'children'),
     Input('signal', 'children')])
def change_refresh_rate(job_id, signal):
    """
    Start refreshing when received new jobid, stop when receive the DONE signal
    """
    if signal == 'DONE':
        return 60*60*1000 #1hr
    return 1*1000 #refresh rate = 1s

@app.callback(
    Output('signal', 'children'),
    [Input('job-id', 'children'),
     Input('update-interval', 'n_intervals')])
def update_result_status(job_id, n_intervals):
    """
    Fetch job results every 1s.
    New jobid trigger PROCESSING signal. Done job triger Done signal.
    """
    job = Queue(connection=conn).fetch_job(job_id)
    if job is not None:
        result_dict = job.result
        if result_dict is None:
            return "PROCESSING"
        return "DONE"

@app.callback(Output('button-div', 'children'),
              [Input('signal', 'children')])
def update_button(signal):
    """
    Update Button Text (Search Status) based on signal.
    """
    if signal == "DONE":
        return items.create_button(message='搜索',
                                   button_type="button-primary", component_id="button")
    if signal == "PROCESSING":
        return items.create_button(message='搜索中，請稍候...',
                                   button_type="button", component_id="button")
    return items.create_button(message='準備中...',
                               button_type="button", component_id="button")

@app.callback(Output('output-df', 'children'),
              [Input('signal', 'children'),
               Input('job-id', 'children')])
def update_df(signal, job_id):
    """
    Fetch and post DataFrame from job when DONE signal is received.
    """
    if signal == "DONE":
        job = Queue(connection=conn).fetch_job(job_id)
        df_collocation = job.result[0]
        table_figure = items.generate_table(df_collocation)
        return table_figure
    df_prepare = pd.DataFrame({'準備中...':np.tile(' ', 15)})
    table_figure = items.generate_table(df_prepare)
    return table_figure

@app.callback(Output('wordcloud', 'src'),
              [Input('signal', 'children'),
               Input('job-id', 'children'),
               ])
def update_image(signal, job_id):
    """
    Fetch and post wordcloud image from job when DONE signal is received.
    """
    if signal == "DONE":
        job = Queue(connection=conn).fetch_job(job_id)
        img = job.result[1]
        image_filename = job.result[2]
        if img:
            img.to_file(image_directory+image_filename)
        print(image_filename)
        return app.get_asset_url(image_filename)
    return app.get_asset_url('blank.png')

# @app.callback(Output('time-log','children'),
#           [Input('signal', 'children'),
#            Input('job-id', 'children')])
# def update_timelog(signal, job_id):
#     """
#     Update Timelog when DONE signal is received
#     """
#     if signal == "DONE":
#         job = Queue(connection=conn).fetch_job(job_id)
#         timelog = job.result[3]
#         return f"""
#         Search Collocation{timelog['collocation']:.2f}
#         Compute Table{timelog['dataframe']:.2f}
#         Generate Wordcloud: {timelog['wordcloud']:.2f}
#         """

if __name__ == '__main__':
    app.run_server(debug=True)
