"""
Interface.py
The main web page interface that the users see.  Uses flask to host the web page and process posts.
Breaks up each part of the Grafana functionality into seperate directories.
The templates folder contains all html templates and css styling for rendering the pages.
"""
from flask import Flask, render_template, redirect, request, jsonify, url_for
from flask_wtf import FlaskForm
from wtforms import SelectField
import DB_Processor
import API_Processor
import pandas as pd
import copy
import os
from string import digits

LOGO_FOLDER = os.path.join('static', 'logo')

__db = DB_Processor.db()
__api = API_Processor.GrafanaAPIProcessor()


""" 
utility function to convert the users time input to a format legible for Grafana

Args:
    input_time: time to convert to grafana format

Returns: JSON of all dashboards info
"""
def convert_time_to_grafana_format(input_time):
    date_time_obj = pd.to_datetime(input_time, utc=True).to_pydatetime()
    date_str = date_time_obj.strftime('%Y-%m-%d %H:%M:%S')
    return date_str

""" 
Checks if the given input is a legible date

Args:
    input_time: value to check if legible time

Returns: bool if is proper date
"""
def is_date_format(input_time):
    try:
        date_time_obj = pd.to_datetime(input_time).to_pydatetime()
        date_time_obj.strftime('%Y-%m-%d %H:%M:%S')
        return True
    except ValueError:
        return False

""" 
Checks if the given input is a legal Grafana time with keyword "now"

Args:
    input_time: value to check if legible time

Returns: True if it is proper formatted "now" time else false
"""
def is_proper_now(input_time):
    if input_time[0: input_time.find('-')].isdigit() or input_time[-1:].isdigit():
        return False

    remove_digits = str.maketrans('', '', digits)
    input_time = input_time.translate(remove_digits)
    input_time = "".join(input_time.split())
    input_time.lower()
    return input_time == "now-h" or input_time == "now-d" or input_time == "now-y"\
        or input_time == "now-m" or input_time == "now-s" or input_time == "now"


""" 
Form for drop down menu
"""
class Form(FlaskForm):
    table = SelectField('table', choices=[])


""" 
Cols for each table are selected by checkboxes which are returned as a list when posted.
The list has to be parsed into a string for the Grafana API

Args:
    cols: Preformatted list with names of tables and cols ex: t000005c05, t000008c04,...

Returns: Formatted list that breaks up the names into a tablecol ex: t000001c02c04c05, t000052c00,c01,c05
"""
def parse_cols(cols):
    tables_cols = []

    for c in cols:
        found = False
        for iterator in tables_cols:
            if c[0:c.find('c')] == iterator[0]:
                iterator.append(c[c.find('c'):])
                found = True
        if not found:
            tables_cols.append([c[0:c.find('c'):]])
            tables_cols[len(tables_cols) - 1].append(c[c.find('c'):])
    return tables_cols


""" 
Cols for each table are selected by checkboxes which are returned as a list when posted.
The list has to be parsed into a string for the Grafana API

Args:
    cols: Preformatted list with names of panels, tables and cols ex: 435t000005c05, 456t000008c04,...

Returns: Formatted list that breaks up the names into a dict for each panel with list of tables and cols
"""
def parse_update_temp(cols):
    panel_template = {
        "id": "",
        "tables": []
    }

    table_template = {
        "table_name": "",
        "cols": ""
    }

    delimiter = '/'
    panels = []
    for c in cols:
        found_panel = False
        for panel in panels:
            if c[0:c.find(delimiter)] == panel['id']:
                index = c.find(delimiter)
                found_panel = True
                found_table = False
                for table in panel['tables']:
                    if table['table_name'] == c[index + 1:c.find(delimiter, index + 1)]:
                        index2 = c.find(delimiter, index + 1)
                        found_table = True
                        table['cols'] = table['cols'] + ", " + c[index2 + 1:] + " AS \"" \
                            + __db.convert_tabname_to_smaxvar(c[index + 1:c.find(delimiter, index + 1)])\
                            + " " + c[index2 + 1:] + '\"'
                        break
                if found_table:
                    break
                if not found_table:
                    index = c.find(delimiter)
                    index2 = c.find(delimiter, index + 1)
                    panel['tables'].append(table_template.copy())
                    panel['tables'][-1]['table_name'] = c[index + 1:c.find(delimiter, index + 1)]
                    panel['tables'][-1]['cols'] = c[index2 + 1:] + " AS \"" \
                        + __db.convert_tabname_to_smaxvar(c[index + 1:c.find(delimiter, index + 1)])\
                        + " " + c[index2 + 1:] + '\"'
                    break

        if not found_panel:
            index = c.find(delimiter)
            panels.append(copy.deepcopy(panel_template))
            panels[-1]['id'] = c[0:index]
            panels[-1]['tables'].append(table_template.copy())
            panels[-1]['tables'][-1]['table_name'] = c[int(index) + 1:int(c.find(delimiter, index + 1))]
            panels[-1]['tables'][-1]['cols'] = c[c.find(delimiter, index + 1) + 1:] + " AS \"" \
                + __db.convert_tabname_to_smaxvar(c[index + 1:c.find(delimiter, index + 1)]) \
                + " " + c[c.find(delimiter, index + 1) + 1:] + '\"'
    return panels


app = Flask(__name__)
app.config['SECRET_KEY'] = 'abcdefg'
app.config['UPLOAD_FOLDER'] = LOGO_FOLDER

""" 
Reroutes base url to the home page
"""
@app.route('/', methods=['GET', 'POST'])
def reroute():
    return redirect(url_for('home'))

""" 
Home page with explination and nav bar
"""
@app.route('/home', methods=['GET', 'POST'])
def home():
    logo = os.path.join(app.config['UPLOAD_FOLDER'], 'sao_logo.jpg')

    return render_template("home.html", logo=logo)


""" 
Page for creating dashboards
"""
@app.route('/create_dash', methods=['GET', 'POST'])
def create_dash():
    form = Form()
    form.table.choices = __db.get_tables("")

    logo = os.path.join(app.config['UPLOAD_FOLDER'], 'sao_logo.jpg')

    if request.method == 'POST':
        request.method = ''

        cols = request.form.getlist('boxes')

        tables_cols = []

        for c in cols:
            found = False
            for iterator in tables_cols:
                if c[0:c.find('c')] == iterator[0]:
                    iterator.append(c[c.find('c'):])
                    found = True
            if not found:
                tables_cols.append([c[0:c.find('c'):]])
                tables_cols[len(tables_cols)-1].append(c[c.find('c'):])

        dash_info = {
            "dash_name": request.form['dash_name'],
            "graph_name": request.form["graph_name"],
            "table": tables_cols,
            "temp": False
        }
        __api.create_dash(dash_info)
        return redirect(url_for('create_dash'))

    return render_template("create_dash.html", form=form, logo=logo)


""" 
Page for creating and embedding temp graphs
"""
@app.route('/temp_graphs', methods=['GET', 'POST'])
def temp_graphs():
    form = Form()
    form.table.choices = __db.get_tables("")

    logo = os.path.join(app.config['UPLOAD_FOLDER'], 'sao_logo.jpg')

    if request.method == 'POST':
        uid = request.form.get('uid')

        if uid is None or uid == "null":
            uid = __api.create_temp_dash()

        if request.form['updated'] == 'true':
            updated_cols = request.form.getlist('update_boxes')
            __api.update_temp_dash(uid, parse_update_temp(updated_cols))

        if request.form.get('yminmax_panel_id') is not None:
            local_min = None
            local_max = None
            for input_min, input_max in zip(request.form.getlist('ymin'), request.form.getlist('ymax')):
                if input_min != "":
                    local_min = input_min
                if input_max != "":
                    local_max = input_max
                if local_min is not None or local_max is not None:
                    break
            if local_max.isdigit() and local_min.isdigit():
                __api.update_y_min_max(True, request.form.get('yminmax_panel_id'), uid, local_min, local_max)

        time_from = None
        time_to = None

        if request.form['time_from'] is not None and request.form['time_from'] != "" \
            and request.form['time_from'].lower().find("now") == -1 \
                and is_date_format(request.form['time_from']):
            time_from = convert_time_to_grafana_format(request.form['time_from'])
        elif is_proper_now(request.form['time_from']):
            time_from = request.form['time_from']

        if request.form['time_to'] is not None and request.form['time_from'] != "" \
            and request.form['time_from'].lower().find("now") == -1 \
                and is_date_format(request.form['time_to']):
            time_to = convert_time_to_grafana_format(request.form['time_to'])
        elif is_proper_now(request.form['time_to']):
            time_to = request.form['time_to']

        if time_to is None or time_to == "":
            time_to = "now"

        if time_from is not None:
            __api.update_dash_time(time_from, time_to, True, uid)

        cols = request.form.getlist('boxes')
        tables_cols = parse_cols(cols)

        src = ""
        if len(cols) != 0:
            panel_info = {
                "graph_name": request.form["graph_name"],
                "table": tables_cols,
                "is_temp": True,
                "uid": uid
            }
            panel_id = __api.insert_new_panel(panel_info)
            src = "http://localhost:3000/d-solo/" + uid + "?refresh=1m&orgId=2&panelId=" + str(panel_id)

        return redirect(url_for('temp_graphs', src=src, time_from=time_from, time_to=time_to, uid=uid))

    return render_template("temp_graphs.html", form=form, logo=logo)

""" 
Page for inserting temp graphs to permenant dash
"""
@app.route('/temp_graphs/insert_graphs', methods=['GET', 'POST'])
def insert_graphs():
    form = Form()
    form.table.choices = __api.get_dash_info_list()

    logo = os.path.join(app.config['UPLOAD_FOLDER'], 'sao_logo.jpg')

    if request.method == 'POST':
        target_uid = form.table.data
        panel_list = request.form.getlist('boxes')
        __api.copy_panels(request.form['uid'], target_uid, panel_list)
        return redirect(url_for('temp_graphs'))

    return render_template("insert_graphs.html", form=form, logo=logo)


""" 
Incompleted page for recreating dashboards in interface and allowing updates
"""
@app.route('/update_dash', methods=['GET', 'POST'])
def update_dash():
    return render_template("update_dash.html")


""" 
Page for deleting pages
"""
@app.route('/delete_dash', methods=['GET', 'POST'])
def delete_dash():
    form = Form()
    form.table.choices = __api.get_dash_info_list()

    logo = os.path.join(app.config['UPLOAD_FOLDER'], 'sao_logo.jpg')

    if request.method == 'POST':
        dash_list = request.form.getlist('boxes')
        for dash in dash_list:
            __api.delete_dash(dash)
        return redirect(url_for('delete_dash'))
    return render_template("delete_dash.html", form=form, list=list, logo=logo)


""" 
Hidden directory for uploading columns for each table
"""
@app.route('/col/<table>')
def col(table):
    cols = __db.get_col(table)

    table_array = []
    for c in cols:
        table_obj = {}
        table_obj['col'] = c
        table_array.append(table_obj)
    return jsonify({'col': table_array})


if __name__ == '__main__':
    app.run(debug=True)



