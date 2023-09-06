import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from google.cloud import bigquery
import folium
from streamlit_folium import folium_static
from geopy.distance import geodesic

# Configura las credenciales desde las secrets de Streamlit
credentials = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])

# Autenticación con BigQuery
client = bigquery.Client(credentials=credentials)

# Creación de la interfaz de usuario
st.title('Sistema de Recomendación de Empresas')

# Entrada de datos del usuario
st.sidebar.header('Entrada de datos')
my_latitude_str = st.sidebar.text_input('Latitude:', '00.00000')
my_longitude_str = st.sidebar.text_input('Longitude:', '00.00000')

# Convierte las cadenas en números de punto flotante
my_latitude = float(my_latitude_str)
my_longitude = float(my_longitude_str)


rubro = st.sidebar.selectbox('line:', ['Restaurants',
        'Shopping',
        'Health and Beauty',
        'Rental Services',
        'Tourism',
        'Entertainment',
        'Health and Hospitals',
        'Sports',
        'Arts and Crafts',
        'Events and Weddings',
        'Automotive',
        'Education and Learning',
        'Veterinary and Pets',
        'Gardening and Home Services',
        'Technology, Networks, Electronics, and Engineering',
        'Industry',
        'Professional Services',
        'Other'])

# Modifica la seleccion para que sirva en la consulta:
rubro = rubro.replace(" ", "").replace(",", "")

# Consulta a BigQuery para obtener las recomendaciones
query = f"""
    SELECT name, latitude, longitude, satisfaction, percent_good_reviews, identificador
    FROM data-ops-mind.New_York.newyork_data
    WHERE {rubro} = 1   
"""
#LIMIT 20
#ORDER BY percent_good_reviews DESC


# Ejecuta la consulta y carga los resultados en un DataFrame
df = pd.read_gbq(query, credentials=credentials, project_id="data-ops-mind")

# Muestra el DataFrame
#st.write("Resultados:")
#st.write(df)


#ESTA PARTE BUSCA LAS MAS CERCANAS
# Coordenadas de referencia (tus coordenadas)
mis_coordenadas = (my_latitude, my_longitude)
# Parámetro para la distancia
distancia_maxima = st.sidebar.slider('Selecciona una distancia máxima (en km):', 1, 100, 10)
# Función para calcular la distancia entre dos puntos
def calcular_distancia(row):
    ubicacion = (row['latitude'], row['longitude'])
    return geodesic(mis_coordenadas, ubicacion).kilometers
if st.sidebar.button('Buscar empresas cercanas'):
    # Aplicar la función de cálculo de distancia al DataFrame
    df['Distancia'] = df.apply(calcular_distancia, axis=1)
    # Filtrar registros dentro de la distancia máxima
    registros_cercanos = df[df['Distancia'] <= distancia_maxima]

    #ESTA PARTE GRAFICA
    st.subheader('Mapa de empresas cercanas')
    # Crear un mapa interactivo con folium
    m = folium.Map(location=[my_latitude, my_longitude], zoom_start=10)
    # Agregar marcadores para los puntos cercanos
    for index, row in registros_cercanos.iterrows():
        folium.Marker([row['latitude'], row['longitude']], tooltip=row[['name','satisfaction']]).add_to(m)
    # Agregar un marcador para tus coordenadas
    folium.Marker([my_latitude, my_longitude], tooltip='Tus Coordenadas', icon=folium.Icon(color='red')).add_to(m)
    # Mostrar el mapa en Streamlit
    folium_static(m)

    # Mostrar los registros cercanos en Streamlit
    st.write(f'Registros cercanos dentro de {distancia_maxima} km de tus coordenadas:')
    
  # Agregar una columna de checkboxes al DataFrame
    registros_cercanos['Seleccionar'] = registros_cercanos.apply(lambda row: st.checkbox("", key=row['identificador']), axis=1)

    # Mostrar el DataFrame con la columna de checkboxes
    st.write(registros_cercanos)