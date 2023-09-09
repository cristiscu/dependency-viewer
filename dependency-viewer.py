"""
Created By:    Cristian Scutaru
Creation Date: Apr 2022
Company:       XtractPro Software
"""

import os, sys
import configparser
import snowflake.connector
from pathlib import Path
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

def getQuery(database, schema, start, reverse):
    """
    generates the SQL query [from the eventual connected database and schema]:
    (1) everything
    (2) starting from a specific database object, received as argument
    """

    # gets everything [from the eventual connected database and schema]
    if start == None:
        query = "select * from snowflake.account_usage.object_dependencies"
        if database != None:
            query += f"\n  where referenced_database = '{database}' and referencing_database = '{database}'"
            if schema != None:
                query += f"\n  and referenced_schema = '{schema}' and referencing_schema = '{schema}'"
        return query

    # build reverse recursive query, starting with a top object
    if reverse:
        return ("with recursive cte as (\n"
            "  select * from snowflake.account_usage.object_dependencies\n"
            f"    where referenced_object_name = '{start}'\n"
            f"      and referenced_database = '{database}'\n"
            f"      and referenced_schema = '{schema}'\n"
            "  union all\n"
            "  select deps.*\n"
            "    from snowflake.account_usage.object_dependencies deps\n"
            "    join cte\n"
            "      on cte.referencing_object_id = deps.referenced_object_id\n"
            "      and cte.referencing_object_domain = deps.referenced_object_domain\n"
            ")\n"
            "select * from cte")

    # build recursive query, starting with a top object
    return ("with recursive cte as (\n"
        "  select * from snowflake.account_usage.object_dependencies\n"
        f"    where referencing_object_name = '{start}'\n"
        f"      and referencing_database = '{database}'\n"
        f"      and referencing_schema = '{schema}'\n"
        "  union all\n"
        "  select deps.*\n"
        "    from snowflake.account_usage.object_dependencies deps\n"
        "    join cte\n"
        "      on deps.referencing_object_id = cte.referenced_object_id\n"
        "      and deps.referencing_object_domain = cte.referenced_object_domain\n"
        ")\n"
        "select * from cte")

class Node:
    def __init__(self, database, schema, start, db, sch, name, type) -> None:
        obj = f'{db}.{sch}.'
        if start is None and database is not None:
            obj = '' if schema is not None else f'{sch}.'
        self.name = f'{obj}{name}'
        self.type = type.lower()

        self.by_id = [];
        self.by_name = [];
        self.by_name_and_id = []

    def addDep(self, dep, by):
        if by == "BY_ID": self.by_id.append(dep)
        elif by == "BY_NAME": self.by_name.append(dep)
        else: self.by_name_and_id.append(dep)

    def getNode(self):
        return f'"{self.name}\\n({self.type})"'
    
    def getEdges(self):
        s = ""
        for dep in self.by_id:
            s += f'  {self.getNode()} -> {dep.getNode()} [ style="dotted" ];\n'
        for dep in self.by_name:
            s += f'  {self.getNode()} -> {dep.getNode()} [ style="dashed" ];\n'
        for dep in self.by_name_and_id:
            s += f'  {self.getNode()} -> {dep.getNode()} [ style="solid" ];\n'
        return s

def getDot(database, schema, start, reverse, cur):
    """
    generates and returns a graph in DOT notation
    """

    query = getQuery(database, schema, start, reverse)
    print("Generated SQL query:")
    print(query)

    objects = [];
    results = cur.execute(query).fetchall()
    for row in results:
        # add referenced object node
        obj = Node(database, schema, start,
            str(row[0]), str(row[1]), str(row[2]), str(row[4]))
        if obj not in objects: objects.append(obj)

        # add referencing object node
        dep = Node(database, schema, start,
            str(row[5]), str(row[6]), str(row[7]), str(row[9]))
        if dep not in objects: objects.append(dep)

        # add referencing -> referenced edge
        by = str(row[10])
        if not reverse: dep.addDep(obj, by)
        else: obj.addDep(dep, by)

    # create DOT nodes and edges
    s = ""
    for obj in objects: s += f'  {obj.getNode()};\n'
    s += '\n'
    for obj in objects: s += obj.getEdges()

    rankdir = "LR" if start == None else "TB"
    dir = "back" if reverse else "forward"
    return ('digraph G {\n\n'
        + f'  graph [ rankdir="{rankdir}" bgcolor="#ffffff" ]\n'
        + f'  node [ style="filled" shape="record" color="SkyBlue" ]\n'
        + f'  edge [ penwidth="1" color="#696969" dir="{dir}" ]\n\n{s}}}\n')

def saveHtml(filename, s):
    """
    save in HTML file using d3-graphviz
    https://bl.ocks.org/magjac/4acffdb3afbc4f71b448a210b5060bca
    https://github.com/magjac/d3-graphviz#creating-a-graphviz-renderer
    """
    s = ('<!DOCTYPE html>\n'
        + '<meta charset="utf-8">\n'
        + '<body>'
        + '<script src="https://d3js.org/d3.v5.min.js"></script>\n'
        + '<script src="https://unpkg.com/@hpcc-js/wasm@0.3.11/dist/index.min.js"></script>\n'
        + '<script src="https://unpkg.com/d3-graphviz@3.0.5/build/d3-graphviz.js"></script>\n'
        + '<div id="graph" style="text-align: center;"></div>\n'
        + '<script>\n'
        + 'var graphviz = d3.select("#graph").graphviz()\n'
        + '   .on("initEnd", () => { graphviz.renderDot(d3.select("#digraph").text()); });\n'
        + '</script>\n'
        + '<div id="digraph" style="display:none;">\n'
        + s
        + '</div>\n')

    print(f"Generating {filename} file...")
    with open(filename, "w") as file:
        file.write(s)

def connect(connect_mode, account, user, role, warehouse, database, schema):

    # (a) connect to Snowflake with SSO
    if connect_mode == "SSO":
        return snowflake.connector.connect(
            account = account,
            user = user,
            role = role,
            database = database,
            schema = schema,
            warehouse = warehouse,
            authenticator = "externalbrowser"
        )

    # (b) connect to Snowflake with username/password
    if connect_mode == "PWD":
        return snowflake.connector.connect(
            account = account,
            user = user,
            role = role,
            database = database,
            schema = schema,
            warehouse = warehouse,
            password = os.getenv('SNOWFLAKE_PASSWORD')
        )

    # (c) connect to Snowflake with key-pair
    if connect_mode == "KEY-PAIR":
        with open(f"{str(Path.home())}/.ssh/id_rsa_snowflake_demo", "rb") as key:
            p_key= serialization.load_pem_private_key(
                key.read(),
                password = None, # os.environ['SNOWFLAKE_PASSPHRASE'].encode(),
                backend = default_backend()
            )
        pkb = p_key.private_bytes(
            encoding = serialization.Encoding.DER,
            format = serialization.PrivateFormat.PKCS8,
            encryption_algorithm = serialization.NoEncryption())

        return snowflake.connector.connect(
            account = account,
            user = user,
            role = role,
            database = database,
            schema = schema,
            warehouse = warehouse,
            private_key = pkb
        )

def main():
    """
    Main entry point of the CLI
    """

    # read profiles_db.conf
    parser = configparser.ConfigParser()
    parser.read("profiles_db.conf")
    section = "default"
    account = parser.get(section, "account")
    user = parser.get(section, "user")
    role = parser.get(section, "role")
    warehouse = parser.get(section, "warehouse")
    database = parser.get(section, "database", fallback=None)
    schema = parser.get(section, "schema", fallback=None)

    # simple object name as command line argument?
    start = None
    if len(sys.argv) >= 2:
        start = sys.argv[1]
        if database == None or schema == None:
            print("You must connect with both a database and a schema when referencing one object!")
            sys.exit(2)
    reverse = len(sys.argv) >= 3 and sys.argv[2].lower() == "--reverse"

    # change this to connect in a different way: SSO / PWD / KEY-PAIR
    connect_mode = "PWD"
    con = connect(connect_mode, account, user, role, warehouse, database, schema)
    cur = con.cursor()

    # get DOT digraph string
    s = getDot(database, schema, start, reverse, cur)
    print("\nGenerated DOT digraph:")
    print(s)
    con.close()

    # save as HTML file
    filename = f"output/{account}"
    if database != None:
        filename += f"-{database}"
        if schema != None:
            filename += f".{schema}"
            if start != None: filename += f".{start}"
    if reverse: filename += "-rev"
    filename += ".html"
    saveHtml(filename, s)

if __name__ == "__main__":
    main()
