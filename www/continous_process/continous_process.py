

"""
Proyecto:  API Machine Learning Predicción de consumo de agua
Archivo: continous_process.py

Este script consituye un script continuo que se ejecuta cada cierto intervalo ( en este caso cada 10 minutos )
1. Conexión al API externo para recibir lecturas del consumo de agua
2. Preprocesamiento de registros (limieza, remuestreo etc.)
3. Calculo del consumo para cada curva de demanda predefinida en la bbdd

"""


import requests, pause, sys, os
from datetime import datetime, timedelta
from mlcustom import *
import logging

logging.basicConfig(filename=os.getcwd()+'/continous_process.log',level=logging.DEBUG)

URL,API_KEY = sys.argv[1],sys.argv[2]

def main():
    try:
        conn = connect()
        to_date = datetime.now(timezone.utc).replace(second=0, microsecond=0)

        # leer desde la base de datos el último registro disponible 
        last_lecture = get_last_lecture(conn)
        from_date =  get_last_sampledatetime(last_lecture,to_date)
        signal_list = get_signals(conn).tagname.tolist()
        PARAMS = generate_dict(from_date.isoformat(), to_date.isoformat(), 0, signal_list)
        r = None
        r = requests.get(url = URL+"/api/NumericSample", params = PARAMS, headers= {'apiKey' : API_KEY }) 
        logging.debug("Status code %s" % str(r.status_code ))  
        if r.status_code == 200 :
            
            # extraer datos en formato json  
            lectures = get_lecture_req(r,URL,API_KEY, from_date.isoformat(), to_date.isoformat(), signal_list)
            logging.debug("Número de registros %s" % len(lectures))  
  
            if lectures:
              
                # asignar el id de la senal 
                df_lectures = pd.DataFrame(lectures)
                df_lectures["fk_signal_id"] = df_lectures.apply( lambda row:  select_id_signal(conn,row.tagName), axis = 1)
                df_lectures = df_lectures.dropna(subset=['sampleValue'])

                #  validar tipo de df_lectures 
                logging.debug("validar tipo de df_lectures  ")  
                df_lectures_cleaned = validate_df_lectures(df_lectures)
                
                # convertir pandas df al array de tuplas
                logging.debug("convert pandas df into array of tuples")  
                lecture_list = list(df_lectures_cleaned[[ "sampleValue","sampleDateTime", "fk_signal_id"]].itertuples(index=False, name=None)) 

                # insertar datos al base de datos (tabla: forecast_lecture)
                logging.debug("insert data to forecast_lecture table")  
                insert_lecture_list(lecture_list)

                # calcular el consumo basando en las señales
                logging.debug("calcular el consumo basando en las señales")  
                calculate_consume(conn)

                # actualizar los avisos
                logging.debug("set other warnings to false")  
                set_false_otherwarnings(conn)
            else:          
                logging.error("No hay datos disponibles o eran insuficientes para calcular la demanda")  
            
        else:
            insert_other_warining("Error al conectar con la base de datos.")
            pass
        conn.close()
    except requests.ConnectionError as e:
        insert_other_warining("Error de conexión con la base de datos Octubre: Asegúrese de que usted, así como la API Swagger, esté conectado al Internet. Asegúrese de que Servicio de Swagger Service esté escuchando en %s"% URL)
        logging.error(e)       
    except requests.Timeout as e:
        insert_other_warining("Error de Timeout: El servidor no pudo completar su solicitud a la API Swagger dentro del período de tiempo establecido")
        logging.error(e)    
    except requests.RequestException as e:
        insert_other_warining("Error: Hubo un error al conectarse a la base de datos Octubre")
        logging.error(e)    
    except KeyboardInterrupt:
        insert_other_warining("Alguien cierro el proceso manualmente. Contactese con el administrador.")
        logging.error(e)    



while True:
    main()
    run__date = floor_dt( datetime.now()+timedelta(minutes = 10) , 10)  # en horas ( Tiempo de precipitaciones que estamos analizando)
    loggin.debug("próxima ejecución a las %s" % run__date)
    pause.until(run__date)