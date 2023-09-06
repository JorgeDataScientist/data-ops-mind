import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from google.cloud import bigquery
import folium
from streamlit_folium import folium_static
from geopy.distance import geodesic
import json

# Configura las credenciales desde las secrets de Streamlit
credentials = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])

# Autenticación con BigQuery
client = bigquery.Client(credentials=credentials)

# Función principal
def main():
    st.title('Sistema de Recomendación de Empresas')

    # Variable de estado
    estado = st.session_state.get('estado', 'entrada_datos')

    if estado == 'entrada_datos':
        entrada_datos()
    elif estado == 'buscar_empresas':
        buscar_empresas()
    elif estado == 'mostrar_reviews':
        mostrar_reviews()

def entrada_datos():
    st.sidebar.header('Entrada de datos')
    my_latitude_str = st.sidebar.text_input('Latitude:', '00.00000')
    my_longitude_str = st.sidebar.text_input('Longitude:', '00.00000')

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
    rubro = rubro.replace(" ", "_").replace(",", "_")

    tables = {'California':'data-ops-mind.California.california_data',
              'Florida':'data-ops-mind.Florida.florida_data', 
              'Illinois':'data-ops-mind.Illinois.illinois_data', 
              'New York':'data-ops-mind.New_York.newyork_data', 
              'Texas':'data-ops-mind.Texas.texas_data'}

    state = st.sidebar.selectbox('States:', ['California','Florida', 'Illinois', 'New York', 'Texas'])

    if state in tables:
        table = tables[state]
    else:
        table = None

    # Consulta a BigQuery para obtener las recomendaciones
    query = f"""
        SELECT name, latitude, longitude, satisfaction, percent_good_reviews, identificador
        FROM {table}
        WHERE {rubro} = 1   
    """

    # Ejecuta la consulta y carga los resultados en un DataFrame
    df = pd.read_gbq(query, credentials=credentials, project_id="data-ops-mind")

    distancia_maxima = st.sidebar.slider('Selecciona una distancia máxima (en km):', 1, 100, 10)

    if st.sidebar.button('Buscar empresas cercanas'):
        st.session_state.my_latitude = my_latitude
        st.session_state.my_longitude = my_longitude
        st.session_state.df = df
        st.session_state.distancia_max = distancia_maxima
        st.session_state.table = table
        st.session_state.rubro = rubro
        st.session_state.estado = 'buscar_empresas'

def buscar_empresas():
    #Obtener distancia máxima:

    # Obtener coordenadas
    my_latitude = st.session_state.my_latitude
    my_longitude = st.session_state.my_longitude
    df = st.session_state.df
    distancia_maxima = st.session_state.distancia_max
    mis_coordenadas = (my_latitude, my_longitude)

    # Función para calcular la distancia entre dos puntos
    def calcular_distancia(row):
        ubicacion = (row['latitude'], row['longitude'])
        return geodesic(mis_coordenadas, ubicacion).kilometers
   
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

    # Mostrar el DataFrame con la columna de checkboxes
    registros_cercanos['Selection'] = False
    edited = st.data_editor(registros_cercanos)
    # Filtrar el DataFrame para obtener el registro marcado como True en 'Selection'
    #registro_seleccionado = edited[edited['Selection'] == True]
    # Extraer el valor de la columna 'identificador' del registro seleccionado
    #identificador_seleccionado = registro_seleccionado.iloc[0]['identificador']
    # Filtrar el DataFrame para obtener los registros marcados como True en 'Selection'
    registros_seleccionados = edited[edited['Selection'] == True]
    # Extraer los valores de la columna 'identificador' de los registros seleccionados y almacenarlos en una lista
    identificadores_seleccionados = registros_seleccionados['identificador'].tolist()


    if st.button('Mostrar reseñas'):
        st.session_state.identificador = identificadores_seleccionados
        st.session_state.estado = 'mostrar_reviews'

def mostrar_reviews():
    identificador = st.session_state.identificador
    table = st.session_state.table 
    rubro = st.session_state.rubro 

    identificadores_str = ', '.join([f"'{id}'" for id in identificador])


    # Consulta a BigQuery para obtener las recomendaciones
    query2 = f"""
        SELECT name, satisfaction, text_list, rating_list, date_list, labels
        FROM `{table}`
        WHERE identificador IN ({identificadores_str}) 
    """
    # Ejecuta la consulta y carga los resultados en un DataFrame
    reviews = pd.read_gbq(query2, credentials=credentials, project_id="data-ops-mind")
    # Función para extraer elementos de la lista JSON interna
    def extract_elements(json_str, key):
        try:
            inner_data = json.loads(json_str)
            inner_list = inner_data[key]["list"]
            
            # Filtrar elementos no nulos y obtener sus valores
            return [element["element"] if element and "element" in element and element["element"] is not None else None for element in inner_list]
        except:
            return []

    # Aplicar las funciones a las columnas correspondientes
    reviews['text_list'] = reviews['text_list'].apply(extract_elements, args=("text_list",))
    reviews['rating_list'] = reviews['rating_list'].apply(extract_elements, args=("rating_list",))
    reviews['date_list'] = reviews['date_list'].apply(extract_elements, args=("date_list",))
    reviews['labels'] = reviews['labels'].apply(extract_elements, args=("labels",))

    # Función para combinar las reseñas, ratings y fechas
    def combinar_review(row):
        resenas = row['text_list']
        ratings = row['rating_list']
        fechas = row['date_list']
        labels = row['labels']
        combined_reviews = []
        
        for i in range(len(resenas)):
            if ratings[i] is not None:
                combined_reviews.append(f"📝Review: {resenas[i]}, ⭐️Rating: {ratings[i]}, 📅Date: {fechas[i]}, 💬Opinion: {labels[i]} ")
        
        return combined_reviews

    # Aplicar la función a cada fila y crear la nueva columna
    reviews['combined_reviews'] = reviews.apply(combinar_review, axis=1)

    for i in range(reviews.shape[0]):
        st.subheader(f'Name: {reviews.name[i]}')
        st.write(f'Satisfaction: {reviews.satisfaction[i]}')
           
        if len(reviews.combined_reviews[i]) > 0:
            for j in range(len(reviews.combined_reviews[i])):
                st.write(f'Review: {reviews.combined_reviews[i][j]}')
        else:
            st.write("No reviews available.")




    if st.button('volver'):
        st.session_state.estado = 'buscar_empresas'


# Ejecutar la función principal
if _name_ == '__main__':
    main()