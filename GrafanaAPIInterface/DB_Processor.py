"""
Database Processor
DB Processor handles queries to the SMA engineering database.  Uses psycopg2 to connect to the database
and query required tables.
"""

import psycopg2
import os


class db:
    __con = psycopg2.connect(user=os.environ.get("DATABASE_USER"),
                             password=os.environ.get("DATABASE_PASS"),
                             host=os.environ.get("DATABASE_HOST"),
                             port=os.environ.get("DATABASE_PORT"),
                             database='smax_engdb')
    """
    Gets all columns for a target table in titles table 
    
    Args:
        search_key: target table
        
    Returns: All columns in target table
    """
    def get_tables(self, search_key):
        cur = self.__con.cursor()
        cur.execute("SELECT * FROM titles WHERE smaxvar LIKE \'%" + search_key + "%\';")
        rows = cur.fetchall()
        return rows

    """
        Converts the given smaxvar table name into it's related tabname from the titles table
        
        Args:
            search_key: target table

        Returns: Targets related tabname
    """
    def convert_smaxvar_to_tabname(self, search_key):
        cur = self.__con.cursor()
        cur.execute("SELECT tabname FROM titles WHERE smaxvar LIKE \'%" + search_key + "%\';")
        rows = cur.fetchone()
        return str(rows)

    """
    Converts the given tabname table name into it's related smaxvar from the titles table

    Args:
        search_key: target table

    Returns: Targets related smaxvar name
    """
    def convert_tabname_to_smaxvar(self, search_key):
        cur = self.__con.cursor()
        cur.execute("SELECT smaxvar FROM titles WHERE tabname LIKE \'%" + search_key + "%\';")
        rows = cur.fetchone()
        return str(rows)[2:len(rows)-4]

    """
    Gets all columns in the specified table

    Args:
        search_key: target table

    Returns: array of columns in target table
   """
    def get_col(self, search_key):
        cur = self.__con.cursor()
        cur.execute("SELECT Column_name FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = \'" + search_key + "\';")
        rows = cur.fetchall()
        return rows
