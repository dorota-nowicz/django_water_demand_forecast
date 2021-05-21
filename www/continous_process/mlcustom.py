#!/usr/bin/python


"""
Proyecto:  API Machine Learning Predicción de consumo de agua
Archivo: mlcustom.py

Este script consituye un script con las funciones personalizadas para el proyecto
"""

import psycopg2, pytz, requests
from config import config
import pandas as pd
from datetime import datetime, timezone , timedelta
import numpy as np
import os, sys
import logging

def resampling_analog_signal(raw_values,raw_index,fecha_ini, fecha_fin, intervalo):

    df = pd.DataFrame(data={'SampleValue': raw_values}, index=raw_index)

    x  = pd.date_range(fecha_ini, fecha_fin, freq=intervalo)
    rs = pd.DataFrame(index=x) ####
    
    # matriz de indices que corresponden al de mas cercanos tiempos despues del cambio de las horas
    idx_after = np.searchsorted(df.index.values, rs.index.values)
    # valores y pasos del tiempo antes/despues del cambio de las horas
    rs['after'] = df.loc[df.index[idx_after], 'SampleValue'].values
    rs['before'] = df.loc[df.index[idx_after - 1], 'SampleValue'].values
    rs['after_time'] = df.index[idx_after]
    rs['before_time'] = df.index[idx_after - 1]
    # calculo del nuevo valor
    rs['span'] = (rs['after_time'] - rs['before_time'])
    rs['after_weight'] = (rs['after_time'] - rs.index) / rs['span']
    rs['before_weight'] = (pd.Series(data=rs.index, index=rs.index) - rs['before_time']) / rs['span']
    rs['Values'] = rs.eval('after * before_weight + before * after_weight') 
    
    return rs.Values

def run_model(df_lecture_24h):
    import pickle
    n_entradas=24*6
    pathname = os.path.dirname(sys.argv[0])
    filename = 'red_neuronal_model.sav'
    fullpathname = os.path.join(pathname,filename)
    # load the model from disk
    model = pickle.load(open(fullpathname, 'rb'))

    datos_estudio = df_lecture_24h.sample_value.values
    datos_estudio_norm = datos_estudio/2000-1
    X_test =datos_estudio_norm.reshape(1,n_entradas)
    logging.debug("inicio modelo")  
    prediccion_norm=model.predict(X_test)
    prediccion=(prediccion_norm+1)/0.0005
    logging.debug("Valores predichos nº %s" % len(prediccion))  
    return prediccion[0]
      
def set_false_otherwarnings(conn):
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE public.forecast_warning SET active=false WHERE fk_consume_id is null;")
        conn.commit()
        cursor.close()
    except Exception as e:
        logging.debug(e)
    return

def select_cosume_last_24h(conn,fk_curve_id,end_date):
        
    initial_datetime = (end_date - timedelta(hours = 24)).isoformat()
    final_datetime = end_date.isoformat()
    sql = """SELECT sample_datetime, sample_value FROM public.forecast_consume 
                WHERE 
            fk_curve_id= '%s' and sample_datetime > '%s' and sample_datetime <= '%s'
            ORDER BY sample_datetime
            """ % (fk_curve_id ,initial_datetime,final_datetime)
    logging.debug(sql)
    consume = pd.read_sql_query(sql,con=conn)
    return consume
    
class DictList(dict):
    def __setitem__(self, key, value):
        try:
            # Assumes there is a list on the key
            self[key].append(value)
        except KeyError: # If it fails, because there is no key
            super(DictList, self).__setitem__(key, value)
        except AttributeError: # If it fails because it is not a list
            super(DictList, self).__setitem__(key, [self[key], value])

def connect():
    """ Connect to the PostgreSQL database server """
    conn = None
    try:
        # read connection parameters
        params = config()
        # connect to the PostgreSQL server
        logging.debug('Connecting to the PostgreSQL database...')
        conn = psycopg2.connect(params)

        # create a cursor
        cur = conn.cursor()
        
        # execute a statement
        logging.debug('PostgreSQL database version:')
        cur.execute('SELECT version()')

        # display the PostgreSQL database server version
        db_version = cur.fetchone()
        logging.debug(db_version)
       
        # close the communication with the PostgreSQL
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        logging.debug(error)
    finally:
        if conn is not None:
            return conn

# SELECT ALL CURVES
def get_curves(conn): 
    sql = """SELECT * FROM public.forecast_curve""" 
    df = pd.read_sql(sql,conn)
    return df

# SELECT ALL SINGLS
def get_signals(conn): 
    sql = """SELECT * FROM public.forecast_signal""" 
    df = pd.read_sql(sql,conn)
    return df
# SELECT ALL FLOWMETERS
def get_flowmeters(conn): 
    sql = """SELECT * FROM public.forecast_flowmeter""" 
    df = pd.read_sql(sql,conn)
    return df

# SELECT LAST LECTURE
def get_last_lecture(conn):
    # check if there is any lecture from the last 24 hours in the lecture table
    sql = """SELECT sample_datetime from public.forecast_lecture where sample_datetime > NOW() - INTERVAL '1 DAY' order by sample_datetime  limit 1 """
    df = pd.read_sql(sql,conn)
    return df

# SELECT LAST CONSUME DATE
def get_last_consume(conn,fk_curve_id):
    sql = """SELECT sample_datetime from public.forecast_consume where fk_curve_id =%s order by sample_datetime limit 1 """ %fk_curve_id
    df = pd.read_sql(sql,conn)
    return df
    
# GET LAST LECTURE SAMPLE DATETIME 
def get_last_sampledatetime(last_lecture,to_date ):
    if last_lecture.empty:
        from_date = to_date - timedelta(hours=24) 
    else:
        from_date = last_lecture.iloc[0].sample_datetime 
    return from_date 
    
def establish_from_date(df,to_date): 
    if df.empty:
        from_date = to_date -timedelta(minutes=10)
    else:
        #from_date = df[0].sample_datetime
        from_date = df.iloc[0].sample_datetime
    return from_date

# preparar datos de entrada al API Swagger 
def prepare_data_dict(conn):
    flowmeter_list =  get_flowmeter(conn).tagname.tolist()
    
    to_date = datetime.now(timezone.utc)
    # read the value of the last lecture. If empty take from the last 10 minuts
    from_date = establish_from_date(get_last_lecture(conn),to_date)
    
    to_date = to_date.isoformat()
    from_date = from_date.isoformat()
    
    return from_date, to_date, flowmeter_list

# defining a params dict for the parameters to be sent to the API 
def generate_dict(from_date, to_date, from_row,signal_list):
    
    PARAMS = DictList()
    PARAMS['From']  = from_date
    PARAMS['To']  = to_date
    PARAMS['FromRow'] = from_row
    PARAMS['RowCount'] = 1000
    for flowmeter in signal_list:
        PARAMS['TagNames'] = flowmeter
        
    return PARAMS

def get_lecture_req(r, URL, API_KEY, from_date, to_date, signal_list):
    data = r.json()['list']
    data_len = len(data)
    # handle response with more than 1000 rows
    if data_len  >= 1000 :
        lecutra_arrays = []
        lecutra_arrays.append(data)
        fromRow = 0
        while data_len >= 1000:
            fromRow = fromRow+1000
            PARAMS = generate_dict(from_date, to_date, fromRow, signal_list)
            r = requests.get(url = URL+"/api/NumericSample", params = PARAMS, headers= {'apiKey' : API_KEY }) 
            data = r.json()['list']
            lecutra_arrays.append(data)
            data_len = len(data)
        lectures = [item for sublist in lecutra_arrays for item in sublist]
    else:
        lectures = data
        
    return lectures

def select_id_signal(conn,tagname):
    sql = ("""SELECT id FROM public.forecast_signal WHERE tagname= '%s'"""% tagname  )
    signal_id = pd.read_sql_query(sql,con=conn).id
    return signal_id.iloc[0]

def insert_other_warining(text):
    """ insert warning into the forecast_warning table  """
    
    sql = """
              INSERT INTO public.forecast_warning(
                     text, sample_datetime, active)
              VALUES ( '%s', NOW(), true);
          """ % text
    conn = None
    logging.debug(sql)
    try:
        # read database configuration
        params = config()
        # connect to the PostgreSQL database
        conn = psycopg2.connect(params)
        # create a new cursor
        cur = conn.cursor()
        # execute the INSERT statement
        cur.execute(sql)
        # commit the changes to the database
        conn.commit()
        # close communication with the database
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        logging.debug(error)
    finally:
        if conn is not None:
            conn.close()

def insert_lecture_list(lecture_list):
    """ insert multiple lecture into the lecture table  """
    sql = """INSERT INTO public.forecast_lecture(sample_value, sample_datetime, fk_signal_id) VALUES(%s,%s,%s)
                ON CONFLICT ON CONSTRAINT u_lecture_datetime_value_signal
              DO UPDATE SET sample_value = EXCLUDED.sample_value"""
    conn = None
    try:
        # read database configuration
        params = config()
        # connect to the PostgreSQL database
        conn = psycopg2.connect(params)
        # create a new cursor
        cur = conn.cursor()
        # execute the INSERT statement
        cur.executemany(sql,lecture_list)
        # commit the changes to the database
        conn.commit()
        # close communication with the database
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        logging.debug(error)
    finally:
        if conn is not None:
            conn.close()
                    
# SELECT ALL SIGNALS

def get_curve_flowmeters(conn,fk_curve_id): 
    sql = """SELECT * FROM public.forecast_flowmeter where id in(SELECT flowmeter_id FROM public.forecast_flowmeter_curves  where curve_id = %s )""" % fk_curve_id
    df = pd.read_sql(sql,conn)
    return df


def get_curve_signals_analog(conn,fk_curve_id): 
    sql = """
            SELECT id, tagname, fk_flowmeter_id, fk_tipo_id FROM public.forecast_signal
                WHERE fk_tipo_id = 1 AND fk_flowmeter_id IN
            (SELECT flowmeter_id FROM public.forecast_flowmeter_curves where curve_id= %s) """ % fk_curve_id

    df = pd.read_sql(sql,conn)
    return df

def prepare_curve_flowmeters_list_id(conn,curve_flowmeters, fk_curve_id):
    curve_flowmeters = get_curve_flowmeters(conn,fk_curve_id)
    curve_flowmeters_list_id_org = curve_flowmeters.id.tolist()
    curve_flowmeters_list_id =  list(filter(None, curve_flowmeters_list_id_org)) 
    curve_flowmeters_list_id = {i for i in curve_flowmeters_list_id}
    return curve_flowmeters_list_id

def get_signal_digital(conn,fk_flowmeter_id):
    sql ="""SELECT id FROM public.forecast_signal WHERE fk_flowmeter_id = %s  and fk_tipo_id = 2 """ % fk_flowmeter_id
    df = pd.read_sql(sql,conn)
    digital_signal_id = None if df.empty else df.iloc[0].id
    return digital_signal_id

def get_signal_id(conn,fk_flowmeter_id):
    sql = """SELECT id FROM public.forecast_signal where fk_flowmeter_id= %s """ % fk_flowmeter_id
    df = pd.read_sql(sql,conn)
    signal_id = None if df.empty else df.iloc[0].id
    return signal_id

def get_curve_lecture(conn,curve_flowmeters_signals_list_id, start_datetime, end_datetime): 
    sql = "SELECT * FROM public.forecast_lecture WHERE fk_signal_id = ANY('%s') and sample_datetime between '%s' and '%s' order by sample_datetime asc;" % (curve_flowmeters_signals_list_id, start_datetime, end_datetime)

    df = pd.read_sql(sql,conn)
    return df

def up_dt(dt, interval):
    replace = (dt.minute // interval)*interval
    return dt.replace(minute = replace, second=0, microsecond=0)
    
def floor_dt(dt, interval):
    replace = (dt.minute // interval)*interval
    return dt.replace(minute = replace, second=0, microsecond=0)

def generate_datetime_index(start_date,end_date):
    return  pd.date_range(start_date, end_date, freq='10Min')

def insert_forecaste_list(forecast_list):
    """ insert multiple forecast into the forecast table  """
    sql = """
             INSERT INTO public.forecast_forecast(sample_value, sample_datetime, fk_curve_id) VALUES(%s,%s,%s)
               ON CONFLICT ON CONSTRAINT forecast_sample_datetime_fk_curve_id
              DO UPDATE SET sample_value = EXCLUDED.sample_value;;
          """
    conn = None
    try:
        # connect to the PostgreSQL database
        conn = connect()
        # create a new cursor
        cur = conn.cursor()
        # execute the INSERT statement
        cur.executemany(sql,forecast_list)
        # commit the changes to the database
        conn.commit()
        # close communication with the database
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        logging.debug(error)
    finally:
        if conn is not None:
            conn.close()
            
def insert_consume_list(consume_list):
    """ insert multiple lecture into the lecture table  """
    
    sql = """
             INSERT INTO public.forecast_consume(sample_value, sample_datetime, fk_curve_id) VALUES(%s,%s,%s)
               ON CONFLICT ON CONSTRAINT consume_sample_datetime_fk_curve_id
              DO UPDATE SET sample_value = EXCLUDED.sample_value;;
          """
    conn = None
    try:
        # read database configuration
        params = config()
        # connect to the PostgreSQL database
        conn = psycopg2.connect(params)
        # create a new cursor
        cur = conn.cursor()
        # execute the INSERT statement
        cur.executemany(sql,consume_list)
        # commit the changes to the database
        conn.commit()
        # close communication with the database
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        logging.debug(error)
    finally:
        if conn is not None:
            conn.close()
            
def prepare_df_final(df_consume_flowmeter, datetime_index, fk_curve_id):
    df_final = pd.DataFrame( columns = ["sample_value", "sample_datetime","fk_curve_id"]) 
    df_final.sample_value = df_consume_flowmeter.sum(axis=1).values
    df_final.sample_datetime = datetime_index
    df_final.fk_curve_id = fk_curve_id
    df_final['sample_datetime']= df_final['sample_datetime'].astype(str)  
    return df_final
    
def prepare_df_final_forecasto(prediccion, datetime_index_forecast, fk_curve_id):
    df_final_forecast = pd.DataFrame( columns = ["sample_value", "sample_datetime","fk_curve_id"]) 
    df_final_forecast.sample_value = prediccion.tolist()
    df_final_forecast.sample_datetime = datetime_index_forecast
    df_final_forecast.fk_curve_id = fk_curve_id
    df_final_forecast['sample_datetime']= df_final_forecast['sample_datetime'].astype(str)  
    return df_final_forecast

def validate_df_lectures(df_lectures):
    check_numeric_values = df_lectures[["sampleValue","fk_signal_id"]].apply(pd.to_numeric, errors='coerce').dropna().index
    df_lectures_cleand = df_lectures.iloc[check_numeric_values]
    df_lectures_cleand.astype({"sampleValue": float, "fk_signal_id": int})
    return df_lectures_cleand

def predict_consume(fk_curve_id,end_date):

    conn = connect()
    df_lecture_24h = select_cosume_last_24h(conn,fk_curve_id,end_date)
    conn.close()
    df_lecture_24h = df_lecture_24h.drop_duplicates(subset=['sample_datetime']) # DEICIDIR COMO TRATAR LOS DUPLICADOS!

    if df_lecture_24h.shape[0] != 144 :
        logging.debug("EL No DE DATOS DE LOS ULTIMOS 24 HORAS NO COINCIDE CON 144")
    else:
        prediccion = run_model(df_lecture_24h)
 
        # sample_datetime for forecast
        start_date_forecast= end_date+timedelta(minutes = 10)
        end_date_forecast = start_date_forecast+timedelta(minutes = 20)
        datetime_index_forecast = generate_datetime_index(start_date_forecast,end_date_forecast)

        df_final_forecast = prepare_df_final_forecasto(prediccion, datetime_index_forecast, fk_curve_id)
        forecast_list = list(df_final_forecast.itertuples(index=False, name=None)) 
        insert_forecaste_list(forecast_list)

    return True


def calculate_consume(conn):

    curves = get_curves(conn).id.values
    for curve_id in curves:
        calculate_consume_curve(curve_id)
    return 

def calculate_consume_curve(fk_curve_id):

    
    # 1. seleccionar caudalimetros de interes
    conn = connect()
    intervalo = 10
    end_date = floor_dt(datetime.now(timezone.utc).astimezone(pytz.timezone('Europe/Madrid')), intervalo)
    #
    last_consume_sampledatetime =  get_last_consume(conn,fk_curve_id)
    if last_consume_sampledatetime.empty:
        start_date = end_date-timedelta(hours = 24)
    else:
        start_date = last_consume_sampledatetime.sample_datetime.iloc[0]
    
    curve_flowmeters = get_curve_flowmeters(conn,fk_curve_id)
    curve_signals_analog = get_curve_signals_analog(conn,fk_curve_id)

    curve_flowmeters_list_id = prepare_curve_flowmeters_list_id(conn, curve_flowmeters, fk_curve_id)
    curve_flowmeters_signlas_list_id = {get_signal_id(conn,fk_flowmeter_id) for fk_flowmeter_id in curve_flowmeters_list_id}
    # 2. seleccionar datos de esos caudalimetros
    curve_lecture = get_curve_lecture(conn,curve_flowmeters_signlas_list_id,start_date.isoformat(),end_date.isoformat())
    conn.close()

    # 3. calcular consumo
    if not curve_lecture.empty:
        end_date = floor_dt(curve_lecture.iloc[-1].sample_datetime, intervalo).astimezone(pytz.timezone('Europe/Madrid'))
        start_date = (floor_dt(curve_lecture.iloc[0].sample_datetime, intervalo)+ timedelta(minutes=intervalo)).astimezone(pytz.timezone('Europe/Madrid'))
        datetime_index = generate_datetime_index(start_date,end_date)

        curve_lecture['sample_datetime'] = curve_lecture.apply(lambda row: row.sample_datetime.astimezone(pytz.timezone('Europe/Madrid')), axis =1 )
        curve_lecture = curve_lecture.drop_duplicates(subset= ['sample_value', 'sample_datetime', 'fk_signal_id'])


        # empty df with all signales ( digital and analog) 
        df_resampled = pd.DataFrame( index =datetime_index, columns = curve_flowmeters_signlas_list_id) 

        # empty df after multiplicaction analog and digital
        df_consume_flowmeter =  pd.DataFrame( index =datetime_index, columns = curve_flowmeters.id.tolist()) 

        for i in curve_flowmeters_signlas_list_id:
            raw_df = curve_lecture[curve_lecture.fk_signal_id ==i]

            if not raw_df.empty:
                raw_dates = raw_df.sample_datetime.tolist()
                start_date_signal = floor_dt(raw_dates[0],intervalo)
                end_date_signal = floor_dt(raw_dates[-1],intervalo)
                df_resampled[i] = resampling_analog_signal(raw_df.sample_value.values,raw_dates,start_date_signal, end_date_signal, str(intervalo)+"Min")
            else:
                df_resampled[i] = [0 for i in range(len(datetime_index))]

        df_resampled_fill_na = df_resampled.apply(lambda x: x.fillna(x.mean()),axis=0)


        conn = connect()

        for index,row in curve_signals_analog.iterrows():
            # get fk_signal_id_digital 
            signal_id_digital = get_signal_digital(conn,row.fk_flowmeter_id)
            # check if signal has digital also
            if signal_id_digital:
                df_consume_flowmeter[row.fk_flowmeter_id] = df_resampled_fill_na[row.id]*df_resampled_fill_na[signal_id_digital]
            else:
                df_consume_flowmeter[row.fk_flowmeter_id] = df_resampled_fill_na[row.id]
            fk_signal_id_digital = None 

        conn.close()
        # 4. insertar consumo en tiempo quasi-real

   
        df_final = prepare_df_final(df_consume_flowmeter, datetime_index, fk_curve_id)

        consume_list = list(df_final.itertuples(index=False, name=None)) 

        insert_consume_list(consume_list)

        # 5. ejecutar el modelo
        predict_consume(fk_curve_id,end_date)

    else:
        text = "No hay datos disponibles o eran insuficientes para calcular la demanda de la curva con el id: "+str(fk_curve_id)
        insert_other_warining(text)

    return
        