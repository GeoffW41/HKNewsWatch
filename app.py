import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
from time import time
import plotly.figure_factory as ff
import os
import glob
import wordcloud
import pandas as pd
import numpy as np
from collections import Counter
import flask
import pickle
import json
from nltk.collocations import BigramAssocMeasures, BigramCollocationFinder
from multiprocessing import Pool
from itertools import product
from rq import Queue
from worker import conn
import uuid
from time import sleep


#wordcloud parameters
font_path = 'assets/AquaKana.ttc'
w = wordcloud.WordCloud(font_path=font_path, background_color='White', font_step=1, min_font_size=8,
width=550, height=620, relative_scaling=0.3, colormap='Dark2')
#Wordcloud image path
image_directory = 'assets/'

app = dash.Dash(__name__)
server = app.server

dropdown_item = dcc.Dropdown(id='keyword',
                             options=[
                                 {'label': '林鄭 ', 'value': '林鄭'},
                                 {'label': '陳茂波', 'value': '陳茂波'},
                                 {'label': '一地兩檢', 'value': '一地兩檢'},
                                 {'label': '土地問題', 'value': '土地'},
                                 {'label': '立法會補選', 'value': '立法會補選'},
                                 {'label': '財政預算', 'value': '財政預算'},
                                 {'label': '登革熱', 'value': '登革熱'},
                                 {'label': '一帶一路', 'value': '一帶一路'},
                                 {'label': '泛民', 'value': '泛民'},
                                 {'label': '建制', 'value': '建制'},
                                 {'label': '南亞', 'value': '南亞'},
                                 {'label': 'LGBT/同性戀', 'value': '同性戀'},
                                 ],
                             value='林鄭',
                             className="dropdowns")

input_item = dcc.Input(id='keyword', type='text',
                       value='None',
                       style={'border':'1px solid Black',
                              'width': '100%'})

def create_button(message, classname):
    obj = html.Button(message, id='button', className=classname,
                       style={"border-radius":"1rem",
                              "width": "100%"})
    return obj

button_initialize = create_button(message='準備中...', classname="button")

app.layout = html.Div(
    [html.Div(children=
              [html.H1(children='媒體監察',
                       style={'textAlign': 'center'}),
               html.Label(children='藉搜索關鍵字附近較常出現的詞語，以了解本港各媒體對各政策、人物、事件的觀點取向或對社會上不同族群的刻板印象。',
                       style={'textAlign': 'center',
                              'font-size': '1.5rem'}),
               html.Hr(style={'color' : 'Black'})],
              className="container u-full-width"),

     html.Div(children=[
         html.Div(children=[
             html.Div(
                 html.Div([
                     html.H6('報章'),
                     dcc.Checklist(id='sourcechoice',
                                   options=[
                                       {'label': '蘋果日報', 'value': 'apple'},
                                       {'label': '明報', 'value': 'mingpao'},
                                       {'label': '東網', 'value': 'oncc'},
                                       {'label': '東方日報', 'value': 'oriental'},
                                       {'label': '香港01', 'value': 'hk01'},
                                       {'label': '巴士的報', 'value': 'bas'},
                                       {'label': '明報即時', 'value': 'mingpaoinstant'},
                                       {'label': '文匯報', 'value': 'wwp'},
                                       {'label': '香港電台', 'value': 'rthk'},
                                       {'label': '熱血時報', 'value': 'passion'}],
                                   values = ['apple', 'mingpao','oriental','hk01','rthk'],
                                   labelStyle={'display': 'inline-block',
                                               'width':'25%'},
                                   inputStyle={'min-height':'1.2rem',
                                               'min-width':'1.2rem'},
                                   className="checklist")],
                          style={"border":'1px solid White',
                                 "height":"100%",
                                 "width":"100%"}),
                 className="eight columns",
                 style={"border":'1px solid White',
                        "height":"100%"}),
             html.Div(children=[
                 html.Div(children=[
                     html.H6('關鍵字'),
                     dcc.RadioItems(id='search-method',
                                    options=[
                                        {'label': '選擇關鍵字', 'value': 'choice'},
                                        {'label': '輸入關鍵字', 'value': 'input'}],
                                    value='choice',
                                    labelStyle={'display': 'inline-block',
                                                'width':'50%'},
                                    inputStyle={'min-height':'1.2rem',
                                                'min-width':'1.2rem'}
                                    )],
                          style={'border':'1px solid White'}),
                 html.Div(id='search-grid',
                          children=[dropdown_item],
                          style={'margin-bottom':'10px'})],
                      style={'border':'1px solid White'},
                      className="four columns")],
                  className="row"),
         html.Div([
             html.Div(id='button-div',
                      children=button_initialize,
                      className="row",
                      style={"textAlign":"center"}),
             html.Div(id='intermediate-value',
                      children='None',
                      className="row",
                      style={'display':'none'}),
             html.Div(id='job-id',
                      className="row",
                      style={'display': 'none'}),
             dcc.Interval(id='update-interval',
                          interval=60*60*5000, # in milliseconds
                          n_intervals=0)],
                  className='row')],
              className="container u-full-width",
              style={"border":'1px solid White'}),

     html.Div([
        html.Div([
            html.Div([
                dcc.Graph(id='output-df', style={'width':'100%'})],
                     className='six columns u-full-width',
                     style={"border":'1px solid White'}),
            html.Div([
                html.Img(id='wordcloud', className='u-full-width')],
                     className='six columns')],
                 className="row")],
              className="container u-full-width")],
    className='container')

@app.callback(
    Output(component_id='search-grid', component_property='children'),
    [Input(component_id='search-method', component_property='value')])
def update_search_method(search_method):
    if search_method == 'choice':
        return dropdown_item
    else:
        return input_item

@app.callback(
     Output(component_id='job-id', component_property='children'),
    [Input(component_id='button', component_property='n_clicks')],
    state=[State('keyword','value'),
           State('sourcechoice','values'),
           State('search-method','value')])
# submit query here
def submit_query(n_click, keyword, sourcechoice, search_method):
    print(n_click, keyword, sourcechoice, search_method)
    q = Queue(connection=conn)
    job_id = str(uuid.uuid4())
    job = q.enqueue_call(func=compare_sources,
                                args=(keyword, sourcechoice),
                                timeout='3m',
                                job_id=job_id)

    return job_id

@app.callback(
    Output('intermediate-value', 'children'),
    [Input('update-interval', 'n_intervals')],
    [State('job-id', 'children')])
def check_results(n_intervals, job_id):

    q = Queue(connection=conn)
    job = q.fetch_job(job_id)
    if job is not None:
        print("Result Checker. Job Found.")
        result_dict = job.result
        if result_dict is None:
            print('result not ready. Sleeping...')
            sleep(0.5)
            return 'None'
        if result_dict is not None:
            print(f"Result Checker. Result Found.")
            return json.dumps(result_dict)
    else:
        return 'None'

@app.callback(
    Output('update-interval', 'interval'),
    [Input('job-id', 'children'),
     Input('update-interval', 'n_intervals')])
def stop_or_start_table_update(job_id, n_intervals):
    q = Queue(connection=conn)
    job = q.fetch_job(job_id)
    if job is not None:
        # the job exists - try to get results
        result = job.result
        if result is None:
            print('Timer Update: no result found. Next update: 5s')
            return 4*1000
        else:
            print('Timer Update: Result found. Next update: 1hr')
            return 60*60*1000
    else:
        return 60*60*1000

@app.callback(Output('button-div','children'),
             [Input('update-interval', 'n_intervals')],
             [State('job-id', 'children'),
              State('sourcechoice','values')])
def update_status(n_intervals, job_id, sourcechoice):
    q = Queue(connection=conn)
    job = q.fetch_job(job_id)
    n_source = len(sourcechoice)
    if job is not None:
        result = job.result
        if result is None:
            message = f'搜索需時約 {2 * n_source} 秒鐘，請稍候...'
            return create_button(message=message, classname="button")
        else:
            message = '搜索'
            return create_button(message=message, classname="button-primary")
    else:
        message = '準備中...'
        return create_button(message=message, classname="button")

@app.callback(Output('output-df','figure'),
             [Input('intermediate-value','children'),
              Input('update-interval', 'n_intervals')])
def update_df(jsonified_data, n_intervals):
    df_collocation = pd.DataFrame()
    if jsonified_data == 'None':
        df_prepare = pd.DataFrame({'準備中...':np.tile(' ',15)})
        table_figure = ff.create_table(df_prepare)
        return table_figure
    else:
        result_dict = json.loads(jsonified_data)
        for key in result_dict.keys():
            df = pd.DataFrame(result_dict[key]).sort_values('Score', ascending=False)
            df = df['Collocation'].rename(index=key)[:15]
            df_collocation = pd.concat([df_collocation, df], sort=False, axis=1)
        df_collocation.rename({'apple':'蘋果日報',
                               'bas':'巴士的報',
                               'hk01':'香港01',
                               'mingpao':'明報',
                               'mingpaoinstant':'明報即時',
                               'oriental':'東方日報',
                               'oncc':'東網',
                               'rthk':'香港電台',
                               'passion':'熱血時報',
                               'wwp':'文匯報'}, axis=1, inplace=True)
        if (df_collocation.isnull().sum().sum()/df_collocation.size) > 0.8:
            df_nodata = pd.DataFrame({'數據不足，請嘗試其他關鍵詞。':np.tile(' ',15)})
            table_figure = ff.create_table(df_nodata)
            return table_figure
        df_collocation.fillna('無效', inplace=True)
        table_figure = ff.create_table(df_collocation)
        return table_figure

@app.callback(Output('wordcloud','src'),
              [Input('intermediate-value','children'),
               Input('update-interval', 'n_intervals')],
               [State('job-id', 'children')])
def update_image(jsonified_data, n_intervals, job_id):
    if jsonified_data == 'None':
        image_filename = 'blank.png'
        return app.get_asset_url(image_filename)

    try:
        result_dict = json.loads(jsonified_data)
        sources = list(result_dict.keys())
        freq_counter = Counter()
        for key in sources:
            df = pd.DataFrame(result_dict[key])
            for i in range(df.shape[0]):
                if df.iloc[i]['Score'] > 0:
                    freq_counter[df.iloc[i]['Collocation']] += df.iloc[i]['Score']
        keyword = df.iloc[0]['Keyword']
        freq_counter[keyword] += freq_counter.most_common()[0][1] * 5

        if len(freq_counter) < 20:
            image_filename = 'nodata.png'
            return app.get_asset_url(image_filename)

        image_filename = create_wordcloud(freq_counter, sources, keyword)
    except:
        image_filename = 'nodata.png'

    return app.get_asset_url(image_filename)

  
def _bidirection_score_ngrams(finder, score_fn, filter_fn):
    """Generates of (ngram, score) pairs as determined by the scoring
    function provided.
    """
    for tup in finder.ngram_fd:
        permutations = [(0, 1), (1, 0)]
        filtereds = [filter_fn(tup[i], tup[j]) for i, j in permutations]
        if all(filtereds):
            continue

        score = finder.score_ngram(score_fn, w1, w2)
        if score is None:
            continue

        for (i, j), filtered in zip(permutations, filtereds):
            if not filtered:
                yield (tup[i], tup[j]), score
                
def bidirection_score_ngrams(finder, score_fn, filter_fn):
    """Returns a sequence of (ngram, score) pairs ordered from highest to
    lowest score, as determined by the scoring function provided.
    """
    return sorted(
        _bidirection_score_ngrams(finder, score_fn, filter_fn), 
        key=lambda t: (-t[1], t[0]),
    )


def get_collocation(keywords, source):
    bgm = BigramAssocMeasures()

    word_filter = lambda w1, w2: keywords != w1 or len(w2) < 2

    filename = f"finder_{source}_trimmed.sav"
    try:
        finder = pickle.load(open(filename, 'rb'))
        scorelist = bidirection_score_ngrams(finder, bgm.likelihood_ratio, word_filter)
        word_pairs, scores = zip(*scorelist)
        key, asso = zip(*word_pairs)

        df_topk = pd.DataFrame({
            'Source': source,
            'Keyword': keywords,
            'Collocation': asso,
            'Score': scores,
        })

        df_topk = df_topk.sort_values('Score', ascending=False)\
        .drop_duplicates('Collocation').reset_index(drop=True)[:80]
    except:
        print(f'Not enough data for keyword {keywords} in {source}')
        df_topk = pd.DataFrame({'Source': np.tile(source, 15),
                                'Keyword': np.tile(keywords, 15),
                                'Collocation': np.tile(np.nan,15),
                                'Score': np.tile(np.nan,15)})
    return df_topk.to_dict()

def compare_sources(keywords, sources=['apple', 'mingpao', 'oncc']):
    result_dict = {}
    with Pool(processes=4) as p:
        results = p.starmap(get_collocation, product([keywords],sources))
    for result in results:
        source = result['Source'][0]
        result_dict[source] = result
    # for source in sources:
    #     result_dict[source] = get_collocation(keywords, source)
    return result_dict

def create_wordcloud(freq_counter, sources, keyword):
    sources.sort()
    sources_str = '_'.join(sources)
    image_filename = f'wordcloud_{keyword}_{sources_str}.png'
    print(image_filename)
    # if os.path.exists(image_directory+image_filename):
    #     return image_filename
    img = w.generate_from_frequencies(freq_counter)
    img.to_file(image_directory+image_filename)
    return image_filename

if __name__ == '__main__':
    app.run_server(debug=True)
