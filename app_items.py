"""
This module contains functions to create plotly items
used by the HKNewsWatch App

To-do: Migrate CSS
"""

import json
import dash_core_components as dcc
import dash_html_components as html
from numpy import random

def create_input(component_id, value='None'):
    """
    Create DCC input item.
    """
    return dcc.Input(id=component_id, type='text',
                     value=value,
                     style={'border':'1px solid Black',
                            'width': '100%'})

def create_dropdown(component_id, item_file):
    """
    Create DCC dropdown with randomized value (Ticked Box) from list
    """
    with open(item_file, 'r') as data:
        item_list = data.read().strip('\n').split('\n')

    options = []
    for k in item_list:
        options.append({'label': k, 'value': k})

    values = random.choice(item_list)

    return dcc.Dropdown(id=component_id,
                        options=options,
                        value=values,
                        className="dropdowns")

def create_button(component_id, message, button_type):
    """
    Create HTML button with specific str mesaage and class(Grey/Normal)
    """
    return html.Button(message, id=component_id, className=button_type,
                       style={"border-radius":"1rem",
                              "width": "100%"})

def create_checklist(component_id, filename):
    """
    Create DCC checklist with randomized value (Ticked Box) from json
    """
    with open(filename, 'r') as data:
        item_dict = json.load(data)

    options = []
    for k, v in [*item_dict.items()]:
        options.append({'label': v, 'value': k}) #changes needed

    values = random.choice(list(item_dict.keys()), 5, replace=False).tolist()

    return dcc.Checklist(id=component_id,
                         options=options,
                         values=values,
                         labelStyle={'display': 'inline-block',
                                     'width':'25%'},
                         inputStyle={'min-height':'1.2rem',
                                     'min-width':'1.2rem'},
                         className="checklist")

def generate_table(dataframe, max_rows=15):
    """
    Generate HTML table from Pandas dataframe
    """
    return html.Table(
        # Header
        [html.Tr([html.Th(col) for col in dataframe.columns])] +
        # Body
        [html.Tr([
            html.Td(dataframe.iloc[i][col]) for col in dataframe.columns
        ]) for i in range(min(len(dataframe), max_rows))],
        className="table u-full-width"
    )
