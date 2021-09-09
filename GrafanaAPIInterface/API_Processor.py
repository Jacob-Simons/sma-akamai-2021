"""
Grafana API Processor
GrafanaAPIProcessor is a class which handles all Grafana API requests.  The Grafana API requires specific formatting
for their requests.  The url variable holds the base url for making any sort of API queries related to dashboards.
In order to access the Grafana API it requires an API key.  There are two keys: one for the main org and one for the
temp org, which holds temporary dashboards.  The Grafana API key is sent through a requests header in the format
"Authorization": "Bearer API_KEY".  Every dashboard API request uses a generic JSON template which is defined
in the PAYLOAD_TEMPLATE variable.  Specific dashboards are accessed through their UID.
Many of the functions only update specific parts of the dashboards such as their time ranges or y min/max
"""

import copy
from datetime import datetime
import requests
import csv
import Panel_Templates
import DB_Processor
import os


class GrafanaAPIProcessor:
    temp_org_api_key = os.environ.get("GRAFANA_API_TEMP_ORG_KEY")
    main_org_api_key = os.environ.get("GRAFANA_API_MAIN_ORG_KEY")
    TEMP_DASH_INITAL_NAME = "TEMP_DASH_INITIALIZER_GET_UID_HERE"
    EVEN_LOG_NAME = 'temp_dash_log_even.csv'
    ODD_LOG_NAME = 'temp_dash_log_odd.csv'
    SERVER = "http://localhost:3000"

    header = {"Authorization": "Bearer "}
    url = 'http://localhost:3000/api/dashboards/db'  # curl -H
    PAYLOAD_TEMPLATE = {
        "dashboard": {
            "id": None,
            "uid": None,
            "title": "",
            "tags": [""],
            "panels": [],
            "time": {
                "from": "now - 24h",
                "to": "now"
            },
            "timezone": "browser",
            "schemaVersion": 0,
            "version": 0,
            "refresh": "25s"
        },
    }

    __db = DB_Processor.db()
    """
    Gets uids and titles of all dashboards in main org
        
    Returns: List with (uid, title)
   """
    def get_dash_info_list(self):
        dash_list = self.get_dash_list(False)
        output = []
        for dash in dash_list:
            option = (dash['uid'], dash['title'])
            output.append(option)
        return output

    """
    Updates time for targeted dashboard
    
    Args:
        time_from: Dashboards new time from arg
        time to: Dashboards new time to arg
        is_temp: decides whether to use main org temp org api key
        dash_uid: target dash uid
    
    Returns: requests post data
   """
    def update_dash_time(self, time_from, time_to, is_temp, dash_uid):
        target_dash = self.get_dash_info_by_uid(is_temp, dash_uid)
        header = self.header.copy()
        header['Authorization'] += self.temp_org_api_key if is_temp else self.main_org_api_key
        target_dash['dashboard']['time']['from'] = time_from
        target_dash['dashboard']['time']['to'] = time_to
        r = requests.post(url=self.url, headers=header, json=target_dash, verify=False)
        return r

    """ 
    Updates targeted dashboard's panels

    Args:
        uid: target dashboards uid
        panel_table_col: preformatted dict with dashes panel ids, tables, and columns

    Returns: requests post data
    """
    def update_temp_dash(self, uid, panel_table_col):
        header = self.header.copy()
        header['Authorization'] += self.temp_org_api_key

        dash = self.get_dash_info_by_uid(True, uid)
        for index, panel in enumerate(dash['dashboard']['panels']):
            for updated_panel in panel_table_col:
                if int(panel['id']) == int(updated_panel['id']):
                    panel['targets'].clear()
                    for table in updated_panel['tables']:
                        new_target = copy.deepcopy(Panel_Templates.QUERY_TEMPLATE)
                        panel['targets'].append(new_target)

                        sql = "SELECT\n  time AS \"time\",\n  " + table['cols'] + "\nFROM "\
                            + table['table_name'] + "\nWHERE $__timeFilter(time)"

                        dash['dashboard']['panels'][index]['targets'][-1]['rawSql'] = sql
                        dash['dashboard']['panels'][index]['targets'][-1]['table'] = table['table_name']
                        dash['dashboard']['panels'][index]['targets'][-1]['select'][0][0]['params'] = table['cols']

        r = requests.post(url=self.url, json=dash, headers=header, verify=False)
        return r

    """ 
    Deletes target dashboard
    
    Args:
        uid: target dashboards uid

    Returns: requests post data
    """
    def delete_dash(self, is_temp, uid):
        header = self.header.copy()
        header['Authorization'] += self.temp_org_api_key if is_temp else self.main_org_api_key

        url = self.SERVER + "/api/dashboards/uid/" + uid
        r = requests.delete(url=url, headers=header, verify=False)
        return r

    """ 
    Copies specific panels from one dashboard in temp org to another dashboard in main org
    
    Args:
        source_uid: Temp org dashboard uid where panels will be copied from
        target_uid: Main org dashboard uid where panels will be copied to.
        panel_ids:  list of panel ids that will be copied

    Returns: requests post data
    """
    def copy_panels(self, source_uid, target_uid, panel_ids):
        header = self.header.copy()
        header['Authorization'] += self.main_org_api_key
        source_dash = self.get_dash_info_by_uid(True, source_uid)
        target_dash = self.get_dash_info_by_uid(False, target_uid)
        target_dash['overwrite'] = True
        for panel in source_dash['dashboard']['panels']:
            for panel_id in panel_ids:
                if int(panel['id']) == int(panel_id):
                    target_dash['dashboard']['panels'].append(panel)

        r = requests.post(url=self.url, json=target_dash, headers=header, verify=False)
        return r

    """ 
    Gets the JSON of a specified dashboard by uid
    
    Args:
        is_temp: decides whether to use main org or temp org api key
        dash_uid: Target dash uid

    Returns: JSON of target dashboard
    """
    def get_dash_info_by_uid(self, is_temp, dash_uid):
        url = "http://localhost:3000/api/dashboards/uid/" + dash_uid
        header = self.header.copy()
        header['Authorization'] += self.temp_org_api_key if is_temp else self.main_org_api_key
        info = requests.get(headers=header, url=url, verify=False)
        return info.json()

    """ 
    Gets the JSON of a specified dashboard by name

    Args:
        is_temp: decides whether to use main org or temp org api key
        dash_name: Target dash name

    Returns: JSON of target dashboard
    """
    def get_dash_info_by_name(self, is_temp, dash_name):
        dash_list = self.get_dash_list(is_temp)
        uid = ""
        for dash in dash_list:
            if dash['title'] == dash_name:
                uid = dash['uid']
                break
        return self.get_dash_info_by_uid(is_temp, uid)

    # updates the y min/max for a panel
    """ 
    Updates the y min max range for a target panel in target dash
    
    Args:
        is_temp: decides whether to use main org or temp org api key
        panel_id: Id of target panel to change y min max
        dash_uid: target dash uid that contains the panel
        input_min: new y min
        input_max: new y max

    Returns: requests post data
    """
    def update_y_min_max(self, is_temp, panel_id, dash_uid, input_min, input_max):
        header = self.header.copy()
        header['Authorization'] += self.temp_org_api_key if is_temp else self.main_org_api_key

        target_dash = self.get_dash_info_by_uid(is_temp, dash_uid)
        for index in range(len(target_dash['dashboard']['panels'])):
            if int(target_dash['dashboard']['panels'][index]['id']) == int(panel_id):

                if input_min is not None:
                    target_dash['dashboard']['panels'][index]['fieldConfig']['defaults']['min'] = input_min
                if input_max is not None:

                    target_dash['dashboard']['panels'][index]['fieldConfig']['defaults']['max'] = input_max
                break

        r = requests.post(url=self.url, headers=header, json=target_dash, verify=False)
        return r

    """ 
    Inserts a new panel in a target dash
    
    Args:
        values: Preformatted dict with target dash uid, new panel info, and org key

    Returns: New panel id
    """
    def insert_new_panel(self, values):
        header = self.header.copy()
        header['Authorization'] += self.temp_org_api_key if values['is_temp'] else self.main_org_api_key

        payload = self.get_dash_info_by_uid(values['is_temp'], values['uid'])
        payload['overwrite'] = True

        new_panel = copy.deepcopy(Panel_Templates.LINE_GRAPH)
        payload['dashboard']['panels'].append(new_panel)
        curr_index = len(payload['dashboard']['panels']) - 1
        with open('panel_id_index.txt', 'r') as f:
            index = f.readline()
            index = int(index)
        with open('panel_id_index.txt', 'w') as f:
            f.writelines(str(index + 1))

        payload['dashboard']['panels'][curr_index]['id'] = index
        payload['dashboard']['panels'][curr_index]['title'] = values['graph_name']

        i = 0
        for table in values['table']:
            new_target = copy.deepcopy(Panel_Templates.QUERY_TEMPLATE)
            payload['dashboard']['panels'][curr_index]['targets'].append(new_target)
            col_list = ""
            for col in range(len(table) - 1):
                col_list += table[col + 1] + " AS \""\
                    + self.__db.convert_tabname_to_smaxvar(table[0]) + " " + table[col + 1] + "\""
                if col + 1 != len(table) - 1:
                    col_list += ","

            sql = "SELECT\n  time AS \"time\",\n  " + col_list + "\nFROM " + table[0] + "\nWHERE $__timeFilter(time)"

            payload['dashboard']['panels'][curr_index]['targets'][i]['rawSql'] = sql
            payload['dashboard']['panels'][curr_index]['targets'][i]['table'] = table[0]
            payload['dashboard']['panels'][curr_index]['targets'][i]['select'][0][0]['params'] = table[1:]
            i += 1

        requests.post(url=self.url, headers=header, json=payload, verify=False)
        return index

    # returns a list of all dashboards in a org depending if is_temp is specified
    """ 
    Gets identification info of all dashboards

    Args:
        is_temp: decides whether to use main org or temp org api key

    Returns: JSON of all dashboards info
    """
    def get_dash_list(self, is_temp):
        url = "http://localhost:3000/api/search?query=%"
        header = self.header.copy()
        header['Authorization'] += self.temp_org_api_key if is_temp else self.main_org_api_key

        dash_list = requests.get(headers=header, url=url, verify=False)
        return dash_list.json()

    # create_dash() creates a new dashboard and panel in it.  It uses the dictionary "values"
    # that is defined in Interface.py.
    """ 
    Creates a new dashboard 
    
    Args:
        values: Preformatted dict with dash info, panel info for dash, and specifier for temp or main org api key

    Returns: requests post info
    """
    def create_dash(self, values):
        header = self.header.copy()
        header['Authorization'] += self.temp_org_api_key if values['temp'] else self.main_org_api_key

        payload = copy.deepcopy(self.PAYLOAD_TEMPLATE)
        payload['dashboard']['title'] = values['dash_name']

        new_panel = copy.deepcopy(Panel_Templates.LINE_GRAPH)
        payload['dashboard']['panels'].append(new_panel)
        payload['dashboard']['panels'][0]['title'] = values['graph_name']

        i = 0
        for table in values['table']:
            new_target = copy.deepcopy(Panel_Templates.QUERY_TEMPLATE)
            payload['dashboard']['panels'][0]['targets'].append(new_target)
            col_list = ""
            for col in range(len(table) - 1):
                col_list += table[col + 1] + " AS \"" + self.__db.convert_tabname_to_smaxvar(table[0])\
                    + table[col + 1] + "\""
                if col + 1 != len(table) - 1:
                    col_list += ","

            sql = "SELECT\n  time AS \"time\",\n  " + col_list + "\nFROM " + table[0] + " WHERE $__timeFilter(time)"

            payload['dashboard']['panels'][0]['targets'][i]['rawSql'] = sql
            payload['dashboard']['panels'][0]['targets'][i]['table'] = table[0]
            payload['dashboard']['panels'][0]['targets'][i]['select'][0][0]['params'] = table[1:]
            i += 1

        r = requests.post(url=self.url, headers=header, json=payload, verify=False)
        return r

    """ 
        Creates a new dash in temp org and names it after its uid

        Returns: uid of the new dash created
        """
    def create_temp_dash(self):
        header = self.header.copy()
        header['Authorization'] += self.temp_org_api_key

        payload = copy.deepcopy(self.PAYLOAD_TEMPLATE)
        payload['dashboard']['title'] = self.TEMP_DASH_INITAL_NAME

        requests.post(url=self.url, headers=header, json=payload, verify=False)

        temp_dash_info = self.get_dash_info_by_name(True, self.TEMP_DASH_INITAL_NAME)
        temp_dash_info['dashboard']['title'] = temp_dash_info['dashboard']['uid']
        uid = temp_dash_info['dashboard']['uid']
        requests.post(url=self.url, headers=header, json=temp_dash_info, verify=False)

        if int(datetime.today().strftime('%d')) % 2 == 1:
            log_file = self.EVEN_LOG_NAME
        else:
            log_file = self.ODD_LOG_NAME

        with open(log_file, 'a') as logs:
            log_writer = csv.writer(logs, delimiter=',')
            log_writer.writerow([uid, str(datetime.now())])

        return uid
