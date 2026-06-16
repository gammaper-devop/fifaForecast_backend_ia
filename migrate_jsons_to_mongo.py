import os
import json
from pathlib import Path
from pymongo import MongoClient, errors
from dotenv import load_dotenv

# Cargar las variables del archivo .env
load_dotenv()

def migrar_datos():
    # 🔌 Leer configuraciones desde las variables de entorno con respaldos por defecto
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    DB_NAME = os.getenv("MONGO_DB_NAME", "mongo-mundial")
    
    # 📁 Leer la ruta de los JSON. Si no está en el .env, usa la raíz del proyecto.
    ruta_env = os.getenv("RUTA_JSON_PARTIDOS")
    if ruta_env:
        DIRECTORIO_JSON = Path(ruta_env)
    else:
        DIRECTORIO_JSON = Path(__file__).resolve().parent

    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
        client.server_info() # Valida conexión con Docker
        
        db = client[DB_NAME]
        coleccion = db["partidos_reales"]
        
        # 🔑 ÍNDICE ÚNICO COMPUESTO: Evita duplicados
        coleccion.create_index(
            [("partido.fecha", 1), ("partido.equipo_local", 1), ("partido.equipo_visitante", 1)], 
            unique=True
        )
        
        print("\n=== 🔄 INICIANDO SINCRONIZACIÓN CON MONGO-MUNDIAL ===")
        print(f"📂 Buscando archivos JSON en: {DIRECTORIO_JSON}")
        
        if not DIRECTORIO_JSON.exists():
            print(f"❌ ERROR: La ruta especificada no existe en este equipo.")
            return

        partidos_nuevos = 0
        partidos_duplicados = 0
        archivos_con_error = 0
        
        # Escanear el directorio configurado
        for archivo in os.listdir(DIRECTORIO_JSON):
            if archivo.endswith('.json') and archivo != 'empty_template.json':
                ruta_completa = DIRECTORIO_JSON / archivo
                try:
                    with open(ruta_completa, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                        # Insertar en la BD
                        coleccion.insert_one(data)
                        print(f"✅ [NUEVO] Guardado con éxito: {archivo}")
                        partidos_nuevos += 1
                        
                except errors.DuplicateKeyError:
                    print(f"⏭️  [OMITIDO] Ya existía en la base de datos: {archivo}")
                    partidos_duplicados += 1
                except json.JSONDecodeError:
                    print(f"❌ [ERROR] {archivo} tiene un error de sintaxis JSON.")
                    archivos_con_error += 1
                except Exception as e:
                    print(f"⚠️  [AVISO] Error en {archivo}: {str(e)}")
                    archivos_con_error += 1
                        
        # 📊 Reporte Ejecutivo Final
        print("\n==================================================")
        print("🏁 PROCESO DE SINCRONIZACIÓN DIARIA TERMINADO")
        print(f"📥 Partidos nuevos indexados hoy: {partidos_nuevos}")
        print(f"🔒 Historial preservado (duplicados omitidos): {partidos_duplicados}")
        if archivos_con_error > 0:
            print(f"⚠️  Archivos corruptos detectados: {archivos_con_error}")
        print("==================================================\n")
        
    except errors.ServerSelectionTimeoutError:
        print("\n❌ ERROR: No se pudo conectar a MongoDB. Revisa tu contenedor Docker.")
    except Exception as e:
        print(f"\n❌ Ocurrió un error crítico: {str(e)}")

if __name__ == "__main__":
    migrar_datos()