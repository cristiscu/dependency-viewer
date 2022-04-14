Snowflake Object Dependency Viewer
==================================

Simple tool to connect to Snowflake and generate a HTML file with a DOT graph that can show all database object dependencies.

# Database Profile File

In the root folder, you need to create a **profiles_db.conf** file with your Snowflake connection parameters, following the template:

<code>[default]</code>  
<code>account = your-snowflake-account</code>  
<code>user = your-username</code>  
<code>role = your-role</code>  
<code>warehouse = your-warehouse</code>  
<code>database = your-database</code>  
<code>schema = your-schema</code>  

The database and schema are optional:
* When connecting with no database and no schema, the tool will get all the data through the new OBJECT_DEPENDENCIES view.
* When connecting with a database, the tool will look only for referenced and referencing objects from this database alone, and will skip the database name in the fully-qualified names of the nodes.
* When connecting with both a database and a schema, the tool will look only for referenced and referencing objects from this database schema alone, and will skip the database and schema names in the fully-qualified names of the nodes.

We connect to Snowflake with the Snowflake Connector for Python. We have code for (a) password-based connection, (b) connecting with a Key Pair, and (c) connecting with SSO. For password-based connection, save your password in a SNOWFLAKE_PASSWORD local environment variable. Never add the password or any other sensitive information to your code or to profile files.

# 1. Show All Dependencies from the Current Account

Connect with no database and no schema, to show a generated SVG graph in a HTML file for all existing dependencies. Call the tool as below:

<code>python dependency-viewer.py</code>  

The following is what I had from my own Snowflake test account:

![All Dependencies](/images/account.png)

All names are fully-qualified, and the rendering if left-to-right, with the objects that depend on other objects on the left. Dotted arrows are for BY_ID dependencies, dashed for BY_NAME, and solid for BY_NAME_AND_ID. We do not show the ID values.

# 2. Show All Dependencies from a Database

Connect with a database name in the profile file, than call the tool exactly like before.

The following is what I had from my own Snowflake test account, connecting with the EmployeesQX database:

![Database Dependencies](/images/account-EmployeesQX.png)

All names are fully-qualified, but with no database name. Referenced or referencing objects from other databases are not included.

# 3. Show All Dependencies from a Database Schema

Connect with a database name in the profile file, than call the tool exactly like before.

The following is what I had from my own Snowflake test account, connecting with the EmployeesQX database:

![Schema Dependencies](/images/account-EmployeesQX.PUBLIC.png)

The names are no longer fully-qualified, because all objects belong to the same database and schema. Referenced or referencing objects from other databases and schemas are not included.

# 4. Show All Dependencies of a Database Object

Connect with both a database and a schema name in the profile file, than call the tool with the simple name of the object:

<code>python dependency-viewer.py checkManagerEmployee</code>  

The following is what I had from my own Snowflake test account, for the EmployeesQX.PUBLIC.checkManagerEmployee user-defined function:

![Object Dependencies](/images/account-EmployeesQX.PUBLIC.checkManagerEmployee.png)

All names are fully-qualified, in case you may have inter-database dependencies. The rendering if now top-down, with your named object on top.
