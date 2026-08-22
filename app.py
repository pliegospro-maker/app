import streamlit as st
# Configuración de página
st.set_page_config(page_title="Pliegos Pro", page_icon="favicon.png", layout="wide", initial_sidebar_state="expanded")

# --- INYECCIÓN DE CSS PERSONALIZADO ---
estilos = """
<style>
    /* Ocultar el header superior y el footer de Streamlit para que se vea más como una web app y menos como un script */
    footer {visibility: hidden;}

    /* Estilos para los botones principales (Efecto Glow Cyan) */
    button[kind="primary"] {
        background-color: #004D4D !important; /* Cyan oscuro */
        border: 1px solid #00FFFF !important; /* Borde brillante */
        box-shadow: 0 0 8px rgba(0, 255, 255, 0.4) !important; /* Resplandor */
        color: white !important;
        border-radius: 8px !important;
        transition: all 0.3s ease;
    }
    
    /* Efecto al pasar el mouse por el botón */
    button[kind="primary"]:hover {
        box-shadow: 0 0 15px rgba(0, 255, 255, 0.7) !important;
        transform: scale(1.02);
    }

    /* Estilos para las cajas de input y selectores para que se fundan con el fondo */
    .stTextInput > div > div > input, .stSelectbox > div > div > div {
        background-color: #0A1118 !important;
        border: 1px solid #3A506B !important;
        color: white !important;
        border-radius: 6px !important;
    }
    
    /* Pequeño glow al hacer foco en un input */
    .stTextInput > div > div > input:focus, .stSelectbox > div > div > div:focus {
        border-color: #00FFFF !important;
        box-shadow: 0 0 5px rgba(0, 255, 255, 0.3) !important;
    }
    /* Estilo para los recuadros de las columnas (Tarjetas flotantes) */
    [data-testid="column"] {
        background-color: #131D26 !important; /* Fondo sutilmente más claro que el fondo general */
        border: 1px solid #1E2D3D !important; /* Borde sutil oscuro */
        border-radius: 12px !important; /* Bordes redondeados */
        padding: 20px !important; /* Espacio interno para que no quede pegado al borde */
        box-shadow: 0 4px 10px rgba(0,0,0,0.3) !important; /* Sombra suave para dar profundidad */
    }
</style>
"""
st.markdown(estilos, unsafe_allow_html=True)
# --- FIN DE INYECCIÓN CSS ---
import mercadopago
from supabase import create_client, Client
import streamlit.components.v1 as components # <--- AGREGAR ESTA LÍNEA


# 1. Conectar a Supabase
url_supabase: str = st.secrets["SUPABASE_URL"]
clave_supabase: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url_supabase, clave_supabase)

# 2. Configurar la memoria temporal
if 'usuario_autenticado' not in st.session_state:
    st.session_state.usuario_autenticado = False

# --- NUEVO SISTEMA DE SESIÓN SEGURO (CON UUID) ---
if "session" in st.query_params:
    token_usuario = st.query_params["session"]
    try:
        # Buscamos quién es el dueño de este token secreto
        respuesta_perfil = supabase.table("perfiles").select("email, creditos").eq("id", token_usuario).execute()
        if len(respuesta_perfil.data) > 0:
            st.session_state.usuario_autenticado = True
            st.session_state.user_id = token_usuario
            st.session_state.email_usuario = respuesta_perfil.data[0]["email"]
        else:
            st.session_state.usuario_autenticado = False
    except:
        st.session_state.usuario_autenticado = False

# 3. Pantalla de Autenticación (Modelo Freemium)
if not st.session_state.usuario_autenticado:
    # --- NUEVO BANNER DE INICIO DE SESIÓN ---
    st.image("bannerweb.png", use_container_width=True)
    st.markdown("<br>", unsafe_allow_html=True) # Un pequeño espacio invisible para que respire el diseño
    
    st.title("🔐 Acceso a PliegosPro")
    tab_login, tab_registro = st.tabs(["Iniciar Sesión", "Crear Cuenta"])

    with tab_login:
            email_login = st.text_input("Tu Email", key="email_login").strip().lower()
            password_login = st.text_input("Tu Contraseña", type="password", key="pass_login")
            
            if st.button("Ingresar al Software", type="primary"):
                try:
            # Inicia sesión directamente
                    respuesta = supabase.auth.sign_in_with_password({"email": email_login, "password": password_login})
                    user_id = respuesta.user.id # Obtenemos el UUID secreto
            
                    st.session_state.usuario_autenticado = True
                    st.session_state.user_id = user_id
                    st.session_state.email_usuario = email_login
            
                    # --- MAGIA SEGURA CONTRA EL F5 ---
                    st.query_params.clear() # Limpiamos basura vieja de la URL
                    st.query_params["session"] = user_id # Guardamos el UUID, no el email
            
                    st.rerun()
                except Exception as e:
                    st.error("Email o contraseña incorrectos.")

                    # === BUSCAR LOS CRÉDITOS A LA CAJA FUERTE ===
                    try:
                        respuesta_bd = supabase.table("perfiles").select("creditos").eq("email", email_login).execute()
                        if len(respuesta_bd.data) > 0:
                            st.session_state.creditos = respuesta_bd.data[0]["creditos"]
                        else:
                            st.session_state.creditos = 0
                    except Exception as error_db:
                        st.session_state.creditos = 0
                        
                    st.rerun()
                except Exception as e:
                    st.error("Email o contraseña incorrectos.")
       

    with tab_registro:
        st.info("Creá tu cuenta gratis. Podés armar tus pliegos y solo pagás cuando quieras descargarlos en alta calidad.")
        email_reg = st.text_input("Nuevo Email", key="email_reg")
        password_reg = st.text_input("Nueva Contraseña (mínimo 6 letras/números)", type="password", key="pass_reg")

        if st.button("Registrarme"):
            try:
                respuesta = supabase.auth.sign_up({"email": email_reg, "password": password_reg})
                user_id = respuesta.user.id
                
                # Anota al usuario en tu tabla
                supabase.table("perfiles").insert({"id": user_id, "email": email_reg}).execute()
                st.success("✅ ¡Cuenta creada con éxito! Ahora podés Iniciar Sesión en la pestaña de al lado.")
            except Exception as e:
                st.error(f"⚠️ Error exacto: {e}")

    # EL ESCUDO (Frena el código acá si no inició sesión)
    st.stop()
# ... (todo lo que ya tenías)
import streamlit as st
from PIL import Image, ImageFilter, ImageDraw
from rectpack import newPacker, PackingMode, PackingBin
import io
import os
import datetime
import zipfile
import requests
from streamlit_cropper import st_cropper
import numpy as np
from streamlit_drawable_canvas import st_canvas

# Ocultar elementos estéticos (Header completo, GitHub, etc.)
ocultar_elementos = """
<style>
/* 1. LA BALA DE PLATA: Oculta toda la mitad derecha del encabezado (Share, GitHub, Menú) */
.stApp > header > div:last-child {display: none !important;}
[data-testid="stToolbar"] {display: none !important;}
[data-testid="stHeaderActionElements"] {display: none !important;}

/* 2. Oculta el globito flotante de "Manage app" de abajo a la derecha */
.viewerBadge_container {display: none !important;}
.viewerBadge_link {display: none !important;}

/* 3. Oculta la marca de agua del pie de página */
footer {display: none !important;}
</style>
"""
st.markdown(ocultar_elementos, unsafe_allow_html=True)

# Constantes
DPI_HIGH = 300
DPI_LOW = 72
PX_PER_CM = int(DPI_HIGH / 2.54)
SHEET_TYPES = {
    "DTF Textil - Estándar (58x100 cm)": {"width_cm": 58, "height_cm": 100},
    "DTF Textil - Angosto (30x100 cm)": {"width_cm": 30, "height_cm": 100},
    "DTF UV - Estándar (57x100 cm)": {"width_cm": 57, "height_cm": 100},
    "DTF UV - Medio Metro (57x50 cm)": {"width_cm": 57, "height_cm": 50}
}
MUESTRA_BG_COLOR = (169, 169, 169, 255) 
HISTORY_BASE_FOLDER = "historial_pliegos"
os.makedirs(HISTORY_BASE_FOLDER, exist_ok=True)

# Colores de fondo para el recuadro de la imagen
BACKGROUND_COLORS = {
    "Blanco": "#FFFFFF",
    "Gris Topo": "#8B8589",
    "Gris Intermedio": "#808080",
    "Gris Oscuro": "#404040",
    "Negro": "#000000"
}

def cm_to_px(cm): return int(cm * PX_PER_CM)
def px_to_cm(px): return px / PX_PER_CM

def get_preview_with_bg(img, bg_hex):
    bg_color = tuple(int(bg_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) + (255,)
    bg_img = Image.new("RGBA", img.size, bg_color)
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    bg_img.paste(img, (0,0), img)
    return bg_img


# --- FILTROS PROFESIONALES ---
def apply_alpha_threshold(img):
    if img.mode != 'RGBA': img = img.convert('RGBA')
    r, g, b, a = img.split()
    a = a.point(lambda p: 255 if p > 50 else 0)
    return Image.merge('RGBA', (r, g, b, a))

def apply_white_choke(img):
    if img.mode != 'RGBA': img = img.convert('RGBA')
    r, g, b, a = img.split()
    a = a.filter(ImageFilter.MinFilter(3))
    return Image.merge('RGBA', (r, g, b, a))

def apply_white_stroke(img, size=5):
    if img.mode != 'RGBA': img = img.convert('RGBA')
    r, g, b, a = img.split()
    stroke_alpha = a.filter(ImageFilter.MaxFilter(size * 2 + 1))
    stroke_img = Image.new('RGBA', img.size, (255, 255, 255, 255))
    stroke_img.putalpha(stroke_alpha)
    return Image.alpha_composite(stroke_img, img)

def remove_specific_color(img, target_hex, tolerance=30):
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    target_hex = target_hex.lstrip('#')
    tr, tg, tb = tuple(int(target_hex[i:i+2], 16) for i in (0, 2, 4))
    
    # --- ACELERACIÓN EXTREMA CON NUMPY ---
    data = np.array(img)
    # Extraemos los canales y los pasamos a formato numérico amplio para evitar errores matemáticos
    r, g, b, a = data[:,:,0].astype(int), data[:,:,1].astype(int), data[:,:,2].astype(int), data[:,:,3]
    
    # Buscamos de golpe todos los píxeles que coinciden con la tolerancia
    mask = (a > 0) & (np.abs(r - tr) <= tolerance) & (np.abs(g - tg) <= tolerance) & (np.abs(b - tb) <= tolerance)
    
    # Volvemos invisibles a todos los seleccionados al mismo tiempo
    data[mask, 3] = 0
    return Image.fromarray(data)

def remove_luminance(img, lum_target, tolerance=30):
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
        
    # --- ACELERACIÓN EXTREMA CON NUMPY ---
    data = np.array(img)
    r, g, b, a = data[:,:,0].astype(int), data[:,:,1].astype(int), data[:,:,2].astype(int), data[:,:,3]
    
    # Calculamos la luz de toda la imagen en una fracción de segundo
    luma = (0.299 * r + 0.587 * g + 0.114 * b).astype(int)
    mask = (a > 0) & (np.abs(luma - lum_target) <= tolerance)
    
    data[mask, 3] = 0
    return Image.fromarray(data)

# Inicializar estados de memoria
if "deleted_images" not in st.session_state: st.session_state.deleted_images = set()
if "image_history" not in st.session_state: st.session_state.image_history = {}
if "last_action_msg" not in st.session_state: st.session_state.last_action_msg = "" 

# --- LECTURA DE CRÉDITOS ---
user_id = st.session_state.user_id
email_usuario = st.session_state.email_usuario

respuesta_perfil = supabase.table("perfiles").select("creditos").eq("id", user_id).execute()
if respuesta_perfil.data:
    creditos_actuales = respuesta_perfil.data[0].get("creditos", 0)
else:
    creditos_actuales = 0

col_titulo, col_billetera = st.columns([3, 1])
# Crear dos columnas: la izquierda más grande (ratio 3) y la derecha más chica (ratio 1)
col_izq, col_der = st.columns([3, 1])

with col_izq:
    # Aquí cargas tu banner actual
    # Asegúrate de poner el nombre correcto de tu archivo de imagen
    st.image("bannerweb.png", use_container_width=True)

with col_der:
    st.markdown("### 👋 Bienvenido/a")
    st.markdown(f"**{email_usuario}**")

    # --- BOTÓN DE CERRAR SESIÓN ---
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.clear() # Borra toda la memoria de la sesión
        st.query_params.clear() # Limpia el token secreto de la URL
        st.rerun() # Recarga la página y te devuelve al inicio
    st.markdown(f"💳 **Tus Créditos:** {creditos_actuales}")
    
    # Botón HTML 100% funcional con estilos en línea
    boton_pago = """
    <a href="https://www.mercadopago.com.ar/checkout/v1/redirect?pref_id=384518284-e8745b6a-0301-4ba4-9e10-e2e6d99a3d2a" target="_blank" style="text-decoration: none;">
        <button style="
            background-color: #004D4D; 
            border: 1px solid #00FFFF; 
            box-shadow: 0 0 8px rgba(0, 255, 255, 0.4); 
            color: white; 
            border-radius: 8px; 
            padding: 10px 15px; 
            cursor: pointer; 
            width: 100%;
            font-weight: bold;
            transition: 0.3s;">
            👉 Recargar 1 Crédito ($5.000)
        </button>
    </a>
    """
    st.markdown(boton_pago, unsafe_allow_html=True)
    

# --- A partir de aquí sigue el resto de tu código normal (1. Configuración, 2. Cargar, etc.) ---
st.divider() # Una línea sutil para separar el header del contenido
    
# Generamos un link automático para 1 crédito
try:
        sdk = mercadopago.SDK(st.secrets["MP_ACCESS_TOKEN"])
        pref_data_billetera = {
            "items": [{"title": "1 Crédito PliegosPro", "quantity": 1, "unit_price": 10.0, "currency_id": "ARS"}],
            "payer": {"email": email_usuario},
            "back_urls": {"success": "https://pliegospro.streamlit.app/"},
            "auto_return": "approved",
            "external_reference": email_usuario,  # <--- EL DNI DEL USUARIO
            "notification_url": "https://hook.us2.make.com/r5og8gzq9xaj9vwbma93aff51ahsx5jb"  # <--- EL TELÉFONO DE TU ROBOT
        }
        res_billetera = sdk.preference().create(pref_data_billetera)
        link_mp_billetera = res_billetera["response"]["init_point"]
        
     

except Exception as e:
        st.error("Error al conectar con Mercado Pago.")
# ---------------------------

if st.session_state.last_action_msg:
    st.toast(st.session_state.last_action_msg)
    st.session_state.last_action_msg = "" 

col1, col2 = st.columns([1, 2.5])

with col1:
    st.subheader("1. Configuración del Pliego")
    sheet_choice = st.selectbox("Tipo de pliego:", list(SHEET_TYPES.keys()))
    sheet_width_cm = SHEET_TYPES[sheet_choice]["width_cm"]
    sheet_height_cm = SHEET_TYPES[sheet_choice]["height_cm"]
    
    margin_cm = st.number_input("Espacio entre imágenes (cm):", min_value=0.3, max_value=1.0, value=0.3, step=0.1)
    margin_px = cm_to_px(margin_cm)
    
    use_edge_margins = st.checkbox("Aplicar márgenes de borde", value=True, help="Deja un espacio libre en los 4 bordes del pliego.")

  # Marca de agua fija y oculta para las descargas gratuitas
    texto_marca = "MUESTRA GRATIS - PLIEGOS PRO" 
    opacidad_marca = 128

    st.subheader("2. Cargar Diseños")
    uploaded_files = st.file_uploader("Subir imágenes", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
    if st.button("🗑️ Limpiar papelera"):
        st.session_state.deleted_images = set()
        st.session_state.image_history = {}
        st.session_state.last_action_msg = "♻️ Papelera limpiada correctamente."
        st.session_state.pliegos_desbloqueados = False # Candado extra
        st.session_state.proceso_iniciado = False # Reiniciamos el proceso
        st.rerun()

# --- PANEL LATERAL Y CLAVES API Y FONDOS ---
edge_margin_px = cm_to_px(0.3) if use_edge_margins else 0
gang_width_px = cm_to_px(sheet_width_cm)
gang_height_px = cm_to_px(sheet_height_cm)
usable_sheet_w_px = gang_width_px - (2 * edge_margin_px)
usable_sheet_h_px = gang_height_px - (2 * edge_margin_px)

with col1:
    st.markdown("---")
    st.markdown("**Personalización**")
    bg_color_choice = st.selectbox("🎨 Color de fondo para recuadros:", list(BACKGROUND_COLORS.keys()), index=1)
    selected_bg_hex = BACKGROUND_COLORS[bg_color_choice]
    
    st.markdown("---")
    st.markdown("**Optimización de Espacio**")
    allow_rotation = st.checkbox("🔄 Permitir rotar imágenes (Tetris)", value=True, help="El sistema evaluará si rotar 90° la imagen ahorra material en el pliego.")
    
    st.markdown("---")
    
    # --- NUEVO ASISTENTE INTEGRADO ---
    with st.expander("🤖 Asistente Virtual 24/7", expanded=False):
        # Usamos el enlace oficial (iframe) de tu bot de Chatbase
        components.iframe("https://www.chatbase.co/chatbot-iframe/qBw1nKTt9az-7COIOZRzd", height=480)
    
    st.markdown("---")

with col2:
                st.subheader("3. Edición de Imágenes")

                # --- ESCUDO ANTI-CORTES ---
                # 1. Guardamos lo que se sube directamente a la caja fuerte de memoria
                if uploaded_files:
                    for file in uploaded_files:
                        if file.name not in st.session_state.image_history:
                            st.session_state.image_history[file.name] = [Image.open(file)]

                # 2. Simulamos la estructura de archivos para no romper tu código inferior
                class ArchivoRecuperado:
                    def __init__(self, name):
                        self.name = name

                # 3. Leemos puramente de la memoria (ignora si la caja de subida se vacía)
                archivos_vivos = [ArchivoRecuperado(nombre) for nombre in st.session_state.image_history.keys() if nombre not in st.session_state.deleted_images]

                # --- LA SOLUCIÓN: Declaramos la variable ACÁ AFUERA ---
                # Así, aunque no haya imágenes, el visor sabe que está vacía y no colapsa
                image_configs = []

                # 4. Mostrar el panel de edición SOLO si hay archivos vivos
                if len(archivos_vivos) > 0:
                    with st.expander("🛠️ Edición Masiva", expanded=False):
                        b_col1, b_col2, b_col3, b_col4 = st.columns([1.5, 1, 1, 1])
                        with b_col1:
                            bulk_dim = st.radio("Ajustar todas por:", ["Ancho", "Alto"], horizontal=True, key="bulk_dim")
                        with b_col2:
                            bulk_val = st.number_input("Medida (cm)", min_value=0.1, value=5.0, step=0.5, key="bulk_val")
                        with b_col3:
                            bulk_qty = st.number_input("Cantidad c/u", min_value=1, value=1, step=1, key="bulk_qty")
                        with b_col4:
                            st.markdown("<br>", unsafe_allow_html=True)
                            if st.button("✅ Aplicar a Todas", type="primary", use_container_width=True):
                                for file in archivos_vivos:
                                    st.session_state[f"qty_{file.name}"] = bulk_qty
                                    if bulk_dim == "Ancho":
                                        st.session_state[f"dim_{file.name}"] = "Ancho"
                                        st.session_state[f"w_{file.name}"] = float(bulk_val)
                                    else:
                                        st.session_state[f"dim_{file.name}"] = "Alto"
                                        st.session_state[f"h_{file.name}"] = float(bulk_val)
                                st.session_state.last_action_msg = "✅ Edición masiva aplicada correctamente."
                                st.rerun()

                    # (Fijate que borramos el image_configs = [] que estaba acá adentro)
                    for idx, file in enumerate(archivos_vivos):
                        img = st.session_state.image_history[file.name][-1]
                        orig_w, orig_h = img.size
                        aspect_ratio = orig_w / orig_h if orig_h != 0 else 1
                        
                        with st.expander(f"⚙️ {file.name}", expanded=False):
                                if len(st.session_state.image_history[file.name]) > 1:
                                    if st.button("↩️ Deshacer último cambio", key=f"undo_{file.name}"):
                                        st.session_state.image_history[file.name].pop()
                                        st.session_state.last_action_msg = f"↩️ Último cambio deshecho en {file.name}."
                                        st.rerun()

                                # --- ELIMINAMOS LA COLUMNA FANTASMA ---
                                # Pasamos a 3 columnas bien proporcionadas
                                c_img, c_size, c_act = st.columns([1, 1.2, 1.2])

                                with c_size:
                                    st.markdown("**📏 Dimensiones**")
                                    dim_choice = st.radio("Ajustar:", ["Ancho", "Alto"], horizontal=True, key=f"dim_{file.name}")
                                    
                                    if dim_choice == "Ancho":
                                        new_w_cm = st.number_input("Ancho (cm)", min_value=0.1, value=round(px_to_cm(orig_w), 2), key=f"w_{file.name}")
                                        new_h_cm = new_w_cm / aspect_ratio
                                        st.caption(f"Alto: {new_h_cm:.2f} cm")
                                        effective_dpi = orig_w / (new_w_cm / 2.54) if new_w_cm > 0 else 300
                                    else:
                                        new_h_cm = st.number_input("Alto (cm)", min_value=0.1, value=round(px_to_cm(orig_h), 2), key=f"h_{file.name}")
                                        new_w_cm = new_h_cm * aspect_ratio
                                        st.caption(f"Ancho: {new_w_cm:.2f} cm")
                                        effective_dpi = orig_h / (new_h_cm / 2.54) if new_h_cm > 0 else 300

                                    # El botón MÁGICO: Solo aparece si la resolución cae por debajo de 250 DPI
                                    if effective_dpi < 250:
                                        st.markdown("<br>", unsafe_allow_html=True)
                                        if st.button("🪄 Mejorar Resolución", key=f"up_{file.name}", use_container_width=True):
                                            with st.spinner("Mejorando resolución..."):
                                                new_size = (orig_w * 2, orig_h * 2)
                                                upscaled = img.resize(new_size, Image.Resampling.LANCZOS)
                                                st.session_state.image_history[file.name].append(upscaled)
                                                st.session_state.last_action_msg = f"🪄 Upscale aplicado correctamente a {file.name}."
                                                st.rerun()
                                    
                                    if st.button("✂️ Recortar Bordes Auto", key=f"crop_{file.name}", use_container_width=True):
                                        # --- RECORTE INTELIGENTE DTF (Canal Alpha) ---
                                        # Detecta solo donde hay tinta real, ignorando las transparencias fantasma
                                        img_rgba = img.convert("RGBA")
                                        bbox = img_rgba.split()[3].getbbox() 
                                        
                                        if bbox:
                                            new_img = img.crop(bbox)
                                            st.session_state.image_history[file.name].append(new_img)
                                            st.session_state.last_action_msg = f"✂️ Bordes vacíos recortados en {file.name}."
                                            st.rerun()
                                        else:
                                            st.toast("⚠️ La imagen está vacía o ya está ajustada.")        
                                    

                                with c_img:
                                    img_for_preview = get_preview_with_bg(img, selected_bg_hex)
                                    st.image(img_for_preview, use_container_width=True)
                                    qty = st.number_input(f"Cantidad", min_value=1, value=1, key=f"qty_{file.name}")
                                    if effective_dpi < 150:
                                        st.warning(f"⚠️ Calidad baja: {int(effective_dpi)} DPI.")

                                with c_act:
                                    st.markdown("**⚙️ Avanzadas (RIP)**")
                                    if st.button("🌑 Asfixia (-1px)", key=f"choke_{file.name}", use_container_width=True):
                                        new_img = apply_white_choke(img)
                                        st.session_state.image_history[file.name].append(new_img)
                                        st.session_state.last_action_msg = f"🌑 Asfixia aplicada a {file.name}."
                                        st.rerun()
                                        
                                    if st.button("⬛ Rellenar Umbral", key=f"thresh_{file.name}", use_container_width=True):
                                        new_img = apply_alpha_threshold(img)
                                        st.session_state.image_history[file.name].append(new_img)
                                        st.session_state.last_action_msg = f"⬛ Umbral aplicado a {file.name}."
                                        st.rerun()
                                        
                                    if "DTF UV" in sheet_choice:
                                        st.markdown("**Estilo Sticker UV**")
                                        
                                        # --- CHAU COLUMNAS ANIDADAS ---
                                        # Ponemos el input y el botón uno debajo del otro
                                        stroke_size = st.number_input("Grosor px", min_value=1, max_value=50, value=15, key=f"stroke_size_{file.name}")
                                        
                                        if st.button("⚪ Reborde", key=f"stroke_{file.name}", use_container_width=True):
                                            new_img = apply_white_stroke(img, size=stroke_size)
                                            st.session_state.image_history[file.name].append(new_img)
                                            st.session_state.last_action_msg = f"⚪ Reborde blanco aplicado a {file.name}."
                                            st.rerun()
                                                
                                    st.markdown("<br>", unsafe_allow_html=True)
                                    if st.button("🗑️ Borrar Imagen", key=f"del_{file.name}", use_container_width=True):
                                        st.session_state.deleted_images.add(file.name)
                                        st.session_state.last_action_msg = f"🗑️ Imagen {file.name} borrada."
                                        st.rerun()

                                st.markdown("---")
                                if st.checkbox("✂️ Recorte Manual (Cropper Avanzado)", key=f"manual_crop_check_{file.name}"):
                                    st.info("Ajusta el recuadro azul para enmarcar el área que deseas conservar. Al terminar, presiona Aplicar.")
                                    cropped_img = st_cropper(img, realtime_update=True, box_color='#0000FF', aspect_ratio=None, key=f"cropper_{file.name}")
                           
                                    if st.button("✅ Aplicar Recorte Manual", key=f"apply_manual_crop_{file.name}", type="primary"):
                                        st.session_state.image_history[file.name].append(cropped_img)
                                        st.session_state.last_action_msg = f"✂️ Recorte manual aplicado en {file.name}."
                                        st.rerun()
                                st.markdown("---")
        
                                # --- AGREGAMOS ESTA LÍNEA QUE SE HABÍA BORRADO ---
                                st.markdown("---")
                                
                                safe_key = "".join(c for c in file.name if c.isalnum())
                                
                                st.markdown("**Quitar Fondos o Colores (Vista Previa en Vivo + Auto-Umbral)**")
                                
                                remove_type = st.radio("Método de borrado:", ["Gotero (Color Exacto)", "Barra (Luminosidad)"], key=f"rm_type_{safe_key}", horizontal=True)
                                
                                if remove_type == "Gotero (Color Exacto)":
                                    cc1, cc2 = st.columns(2)
                                    with cc1:
                                        target_color = st.color_picker("Color (Clica para usar el gotero)", "#000000", key=f"cp_{safe_key}")
                                    with cc2:
                                        tol_val = st.slider("Tolerancia", 0, 100, 30, key=f"tol_exact_{safe_key}")
                                        
                                    preview_img = remove_specific_color(img, target_color, tol_val)
                                    
                                    prev_col1, prev_col2 = st.columns([2, 1])
                                    with prev_col1:
                                        st.image(get_preview_with_bg(preview_img, selected_bg_hex), caption="Previsualización en tiempo real", use_container_width=True)
                                    with prev_col2:
                                        st.markdown("<br><br>", unsafe_allow_html=True)
                                        if st.button("✅ Aplicar Color", key=f"apply_color_{safe_key}", type="primary"):
                                            # Auto-recorte inteligente de bordes fantasma
                                            img_rgba = preview_img.convert("RGBA")
                                            bbox = img_rgba.split()[3].getbbox()
                                            final_img = preview_img.crop(bbox) if bbox else preview_img
                                    
                                            st.session_state.image_history[file.name].append(final_img)
                                            st.session_state.last_action_msg = f"✅ Color borrado y bordes auto-recortados."
                                            st.rerun()
                                else:
                                    # Opción de la Barra de Luminosidad
                                    lum_target = st.slider("Luminosidad a borrar (0=Negro, 255=Blanco)", 0, 255, 255, key=f"lum_{safe_key}")
                                    tol_lum = st.slider("Tolerancia", 0, 100, 30, key=f"tol_lum_{safe_key}")
                                    preview_img = remove_luminance(img, lum_target, tol_lum)
                                    
                                    prev_col1, prev_col2 = st.columns([2, 1])
                                    with prev_col1:
                                        st.image(get_preview_with_bg(preview_img, selected_bg_hex), caption="Previsualización Luminosidad", use_container_width=True)
                                    with prev_col2:
                                        st.markdown("<br><br>", unsafe_allow_html=True)
                                        if st.button("✅ Aplicar Lum", key=f"apply_lum_{safe_key}", type="primary"):
                                            # Auto-recorte inteligente de bordes fantasma
                                            img_rgba = preview_img.convert("RGBA")
                                            bbox = img_rgba.split()[3].getbbox()
                                            final_img = preview_img.crop(bbox) if bbox else preview_img
                                    
                                            st.session_state.image_history[file.name].append(final_img)
                                            st.session_state.last_action_msg = f"✅ Luminosidad borrada y bordes auto-recortados."
                                            st.rerun()

# --- LA PIEZA VITAL QUE FALTABA ---
                                # Pre-calculamos una miniatura ultraliviana acá para no sobrecargar la RAM después
                                preview_scale = 0.1
                                thumb_w = max(1, int(cm_to_px(new_w_cm) * preview_scale))
                                thumb_h = max(1, int(cm_to_px(new_h_cm) * preview_scale))
                                thumb_img = img.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS).convert('RGBA')

                                # Esto registra la imagen para que el Visor la muestre en el pliego
                                image_configs.append({
                                    "image": img,
                                    "thumb": thumb_img, # Guardamos la miniatura lista para usar
                                    "w_px": cm_to_px(new_w_cm),
                                    "h_px": cm_to_px(new_h_cm),
                                    "qty": qty
                                })
            
# --- ACTUALIZAR VISOR EN VIVO ---
if len(image_configs) > 0:
    live_packer = newPacker(mode=PackingMode.Offline, bin_algo=PackingBin.BFF, rotation=allow_rotation)
    # 1. AUMENTAMOS EL COUNT a 20 para que el algoritmo arme todos los pliegos necesarios
    live_packer.add_bin(usable_sheet_w_px, usable_sheet_h_px, count=20) 
    
    rect_id = 0
    rect_map_live = {}
    
    for config in image_configs:
        for _ in range(config["qty"]):
            req_w = config["w_px"] + (margin_px * 2)
            req_h = config["h_px"] + (margin_px * 2)
            live_packer.add_rect(req_w, req_h, rect_id)
            rect_map_live[rect_id] = config
            rect_id += 1
            
    live_packer.pack()
    all_live_rects = live_packer.rect_list()
    
    # 2. AGRUPAMOS LOS RESULTADOS POR PLIEGO (bin_id)
    bins_live = {}
    for rect in all_live_rects:
        b_id = rect[0]
        if b_id not in bins_live:
            bins_live[b_id] = []
        bins_live[b_id].append(rect)
        
    preview_scale = 0.1
    mini_w = int(gang_width_px * preview_scale)
    mini_h = int(gang_height_px * preview_scale)
    
    # 3. GENERAMOS UNA LISTA DE IMÁGENES (UNA POR CADA PLIEGO)
    minimapas = []
    
    for bin_id in sorted(bins_live.keys()):
        minimap = Image.new("RGBA", (mini_w, mini_h), (240, 240, 240, 255))
        draw = ImageDraw.Draw(minimap)
        
        if use_edge_margins:
            safe_x0, safe_y0 = int(edge_margin_px * preview_scale), int(edge_margin_px * preview_scale)
            safe_x1, safe_y1 = mini_w - safe_x0, mini_h - safe_y0
            draw.rectangle([safe_x0, safe_y0, safe_x1, safe_y1], outline=(200, 200, 200, 255), width=1)
            
        for rect in bins_live[bin_id]:
            b, x, y, w, h, rid = rect
            conf = rect_map_live[rid]
            req_w_margin = conf["w_px"] + (margin_px * 2)
            req_h_margin = conf["h_px"] + (margin_px * 2)
            is_rotated = False
            if w == req_h_margin and h == req_w_margin and w != h:
                is_rotated = True
                
            px0 = int((x + edge_margin_px) * preview_scale)
            py0 = int((gang_height_px - (y + h) - edge_margin_px) * preview_scale)
            pw = int(w * preview_scale)
            ph = int(h * preview_scale)
            
            if pw > 0 and ph > 0:
                thumb = conf["thumb"]
                if is_rotated:
                    thumb = thumb.rotate(90, expand=True)
                minimap.paste(thumb, (px0, py0), thumb)
                    
            draw.rectangle([px0, py0, px0 + pw, py0 + ph], outline=(50, 100, 200, 100), width=1)
                    
        minimapas.append(minimap)
# 4. MOSTRAMOS EL VISOR AL FINAL DEL RECORRIDO (Para Celulares y PC)
    with st.expander("🔍 VISOR DE VISTA PREVIA Y FICHA TÉCNICA", expanded=True):
        if len(minimapas) > 1:
            # Creamos los nombres dinámicos de las pestañas
            tabs_preview = st.tabs([f"Pliego {i+1}" for i in range(len(minimapas))])
            for i, tab in enumerate(tabs_preview):
                with tab:
                    st.image(minimapas[i], use_container_width=True)
        elif len(minimapas) == 1:
            # Si es un solo pliego, no ponemos pestañas
            st.image(minimapas[0], use_container_width=True)
            
        # --- NUEVA FICHA TÉCNICA PROFESIONAL ---
        st.markdown("---")
        st.markdown("### 📋 Ficha Técnica")
        
        total_designs = sum([c["qty"] for c in image_configs])
        
        # Calculamos el % de uso del material
        area_total_pliego = sheet_width_cm * sheet_height_cm * len(minimapas)
        area_usada = 0
        for conf in image_configs:
            # Convertimos los píxeles de vuelta a CM para calcular el área
            area_usada += (conf["w_px"] / PX_PER_CM) * (conf["h_px"] / PX_PER_CM) * conf["qty"]
        
        porcentaje_uso = (area_usada / area_total_pliego) * 100 if area_total_pliego > 0 else 0
        
        st.markdown(f"""
        * **Medida:** {sheet_width_cm} × {sheet_height_cm} cm
        * **Diseños totales:** {total_designs}
        * **Aprovechamiento:** {porcentaje_uso:.1f}%
        * **Resolución Final:** 300 DPI
        """)

        # 5. ACTUALIZAMOS LOS MENSAJES DE ESTADÍSTICAS
        if len(all_live_rects) < rect_id:
            st.warning(f"⚠️ Límite alcanzado: {rect_id - len(all_live_rects)} ítems quedaron fuera (máx. 20 pliegos).")
        else:
            if len(minimapas) > 1:
                st.info(f"ℹ️ Estás utilizando {len(minimapas)} pliegos.")
            else:
                st.success(f"✅ Todo entra perfecto en 1 pliego.")

        # 6. Generador Final
        if uploaded_files and len(image_configs) > 0:
            st.markdown("---")

            # 1. Creamos la memoria
            if "proceso_iniciado" not in st.session_state:
                st.session_state.proceso_iniciado = False

            # 2. El botón ahora solo enciende la memoria y BLOQUEA las descargas nuevas
            if st.button("🚀 Generar Archivos Finales", type="primary", use_container_width=True):
                st.session_state.proceso_iniciado = True
                
                # --- EL CANDADO (MAGIA ACÁ) ---
                # Forzamos a que vuelva a cobrar cada vez que se genera un pliego nuevo
                st.session_state.pliegos_desbloqueados = False
   
        
    # 3. Todo tu código pasa a depender de la memoria
    if st.session_state.proceso_iniciado:
        with st.spinner("Procesando pliegos de impresión estricta..."):
            
            packer = newPacker(mode=PackingMode.Offline, bin_algo=PackingBin.BFF, rotation=allow_rotation)
            packer.add_bin(usable_sheet_w_px, usable_sheet_h_px, count=20)
            
            rect_id = 0
            rect_map = {} 
            for config in image_configs:
                for _ in range(config["qty"]):
                    req_w = config["w_px"] + (margin_px * 2)
                    req_h = config["h_px"] + (margin_px * 2)
                    packer.add_rect(req_w, req_h, rect_id)
                    rect_map[rect_id] = config
                    rect_id += 1
                    
            packer.pack()
            all_placed_rects = packer.rect_list()
            
            bins_rects = {}
            for rect in all_placed_rects:
                b_id = rect[0]
                if b_id not in bins_rects: bins_rects[b_id] = []
                bins_rects[b_id].append(rect)
                
            sheets_used = sorted(list(bins_rects.keys()))
            
            now = datetime.datetime.now()
            folder_name = os.path.join(HISTORY_BASE_FOLDER, now.strftime("%Y-%m-%d"), now.strftime("%H%M%S"))
            os.makedirs(folder_name, exist_ok=True)
            
            gang_files_high, gang_files_low = [], []
            
            for i, bin_id in enumerate(sheets_used):
                gang_high_res = Image.new("RGBA", (gang_width_px, gang_height_px), (255, 255, 255, 0))
                
                for rect in bins_rects[bin_id]:
                    _, x, y, w, h, rid = rect
                    conf = rect_map[rid]
                    
                    req_w_margin = conf["w_px"] + (margin_px * 2)
                    req_h_margin = conf["h_px"] + (margin_px * 2)
                    is_rotated = False
                    if w == req_h_margin and h == req_w_margin and w != h:
                        is_rotated = True
                            
                    resized_img = conf["image"].resize((conf["w_px"], conf["h_px"]), Image.Resampling.LANCZOS)
                    if resized_img.mode != 'RGBA':
                        resized_img = resized_img.convert('RGBA')
                    if is_rotated:
                        resized_img = resized_img.rotate(90, expand=True)

                    paste_x = x + edge_margin_px + margin_px
                    paste_y = gang_height_px - (y + h) - edge_margin_px + margin_px
                    
                    gang_high_res.paste(resized_img, (paste_x, paste_y), resized_img)
                
                high_filename = os.path.join(folder_name, f"pliego_{i+1}_alta.png")
                gang_high_res.save(high_filename, format='PNG', dpi=(DPI_HIGH, DPI_HIGH))
                gang_files_high.append(high_filename)
                
                scale_factor = DPI_LOW / DPI_HIGH
                prev_w, prev_h = int(gang_width_px * scale_factor), int(gang_height_px * scale_factor)
                preview_sheet = Image.new("RGBA", (prev_w, prev_h), MUESTRA_BG_COLOR)
                final_sheet_low = Image.new("RGBA", (prev_w, prev_h), (255, 255, 255, 0))

                # --- OPTIMIZACIÓN EXTREMA DE RAM ---
                # Armamos la muestra gratis reduciendo imágenes individuales en vez de todo el lienzo gigante
                for rect in bins_rects[bin_id]:
                    _, x, y, w, h, rid = rect
                    conf = rect_map[rid]
                    req_w_margin = conf["w_px"] + (margin_px * 2)
                    req_h_margin = conf["h_px"] + (margin_px * 2)
                    is_rotated = (w == req_h_margin and h == req_w_margin and w != h)
                            
                    low_w, low_h = int(conf["w_px"] * scale_factor), int(conf["h_px"] * scale_factor)
                    low_img = conf["image"].resize((max(1, low_w), max(1, low_h)), Image.Resampling.LANCZOS).convert('RGBA')
                    if is_rotated:
                        low_img = low_img.rotate(90, expand=True)

                    paste_x = int((x + edge_margin_px + margin_px) * scale_factor)
                    paste_y = int((gang_height_px - (y + h) - edge_margin_px + margin_px) * scale_factor)
                    final_sheet_low.paste(low_img, (paste_x, paste_y), low_img)
                            
                preview_sheet.paste(final_sheet_low, (0, 0), final_sheet_low)
                watermark_file = None

         # --- INICIO MARCA DE AGUA AUTOMÁTICA ---
                ruta_logo = "logo.png"
                if os.path.exists(ruta_logo):
                    wm_img = Image.open(ruta_logo).convert("RGBA")
                    wm_w = 250 # Tamaño del logo a lo ancho
                    wm_h = int(wm_w * (wm_img.height / wm_img.width))
                    wm_img = wm_img.resize((wm_w, wm_h), Image.Resampling.LANCZOS)
                    alpha = wm_img.split()[3]
                    alpha = Image.eval(alpha, lambda a: int(a * 0.7)) # Opacidad al 70%
                    wm_img.putalpha(alpha)
                    
                    watermark_layer = Image.new("RGBA", preview_sheet.size, (255, 255, 255, 0))
                    for y_pos in range(0, prev_h, wm_h + 80):
                        for x_pos in range(0, prev_w, wm_w + 80):
                            watermark_layer.paste(wm_img, (x_pos, y_pos), wm_img)
                    preview_sheet = Image.alpha_composite(preview_sheet, watermark_layer)
                # --- FIN MARCA DE AGUA AUTOMÁTICA ---   

                low_filename = os.path.join(folder_name, f"muestra_{i+1}_cliente.png")
                preview_sheet.save(low_filename, format='PNG', dpi=(DPI_LOW, DPI_LOW))
                gang_files_low.append(low_filename)

           # --- SISTEMA DE DESCARGAS Y CRÉDITOS ---
        cantidad_pliegos = len(sheets_used)
        st.success(f"¡Proceso completado! Se armaron {cantidad_pliegos} pliegos.")
        
        # Guardar temporalmente los archivos para no perderlos si la página se recarga
        if "pliegos_desbloqueados" not in st.session_state:
            st.session_state.pliegos_desbloqueados = False
            
        col_d1, col_d2 = st.columns(2)
        
       # Asegurarnos de que la variable exista en la memoria antes de usarla
        if "pliegos_desbloqueados" not in st.session_state:
            st.session_state.pliegos_desbloqueados = False

        # 1. Creamos el ZIP de Muestra Gratis
        zip_buffer_low = io.BytesIO()
        with zipfile.ZipFile(zip_buffer_low, 'w') as zip_file:
            for f in gang_files_low:
                zip_file.write(f, os.path.basename(f))
        
        # EL SECRETO: Extraer los bytes reales para que no se pierdan al recargar
        zip_bytes_low = zip_buffer_low.getvalue() 
        
        with col_d1:
            st.info("👀 **Vista previa gratis**\n(72 DPI y con marca de agua).")
            st.download_button(
                label="📥 Descargar Muestras", 
                data=zip_bytes_low, 
                file_name="muestras_cliente.zip", 
                mime="application/zip"
            )
# 2. Creamos el ZIP de Alta Resolución (Bloqueado)
        zip_buffer_high = io.BytesIO()
        with zipfile.ZipFile(zip_buffer_high, 'w') as zip_file:
            for f in gang_files_high:
                zip_file.write(f, os.path.basename(f))
                
        # EL BLINDAJE DEFINITIVO: Lo anclamos a la memoria de Streamlit
        st.session_state.zip_final_alta = zip_buffer_high.getvalue()
        with col_d2:
            st.warning(f"🖨️ **Archivos de impresión (300 DPI)**\nCosto total: {cantidad_pliegos} créditos.")
            
            if st.session_state.pliegos_desbloqueados:
                st.success("✅ ¡Desbloqueado! Listo para imprimir.")
                
                # ---> LÍNEA DETECTIVE ACÁ <---
                # st.write(f"🕵️‍♂️ Tamaño del ZIP: {len(st.session_state.zip_final_alta)} bytes")
                
                # Le pasamos los datos directamente desde la memoria
                st.download_button(
                    label="🖨️ Descargar Archivos Finales", 
                    data=st.session_state.zip_final_alta, 
                    file_name="pliegos_alta.zip", 
                    mime="application/zip", 
                    type="primary"
                )
            else:
                if creditos_actuales >= cantidad_pliegos:
                    if st.button(f"💎 Usar {cantidad_pliegos} Créditos para Desbloquear", use_container_width=True):
                            
                       # --- NUEVO DESCUENTO BLINDADO (Transacción Atómica en Supabase) ---
                       respuesta_rpc = supabase.rpc("descontar_creditos", {"usuario_id": st.session_state.user_id, "cantidad": cantidad_pliegos}).execute()
                            
                       if respuesta_rpc.data == True:
                           st.session_state.pliegos_desbloqueados = True
                           st.rerun() # Recargamos para mostrar el botón de descarga
                       else:
                           st.error("❌ No tenés créditos suficientes o la sesion expiró.")
                    
                    # Generamos el link por el total de créditos que le faltan
                    try:
                        creditos_faltantes = cantidad_pliegos - creditos_actuales
                        precio_total = float(creditos_faltantes * 5000)
                        
                        sdk = mercadopago.SDK(st.secrets["MP_ACCESS_TOKEN"])
                        pref_data_peaje = {
                            "items": [{"title": f"{creditos_faltantes} Créditos PliegosPro", "quantity": 1, "unit_price": precio_total, "currency_id": "ARS"}],
                            "payer": {"email": email_usuario},
                            "back_urls": {"success": "TU_LINK_DE_STREAMLIT_AQUI"},
                            "auto_return": "approved",
                            "external_reference": email_usuario,
                            "notification_url": "https://hook.us2.make.com/r5og8gzq9xaj9vwbma93aff51ahsx5jb"
                        }
                        res_peaje = sdk.preference().create(pref_data_peaje)
                        link_mp_peaje = res_peaje["response"]["init_point"]
                        
                        st.markdown(f"[👉 Comprar los {creditos_faltantes} créditos que faltan aquí]({link_mp_peaje})")
                    except Exception as e:
                        st.write("Cargando botón de pago...")            
