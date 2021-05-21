import os

def config():

    database=os.environ["DB_NAME"] 
    user=os.environ["DB_USERNAME"] 
    password=os.environ["DB_PASSWORD"] 
    host=os.environ["DB_HOSTNAME"] 

    str_db ="dbname=%s user=%s password=%s host=%s" % (database,user,password, host )

    return str_db
