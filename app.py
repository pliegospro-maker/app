import streamlit as st
import mercadopago
from supabase import create_client, Client

# 1. Conectar a Supabase
url_supabase: str = st.secrets["SUPABASE_URL"]
clave_supabase: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url_supabase, clave_supabase)

# 2. Configurar la memoria temporal
if 'usuario_autenticado' not in st.session_state:
    st.session_state.usuario_autenticado = False

# === NUEVO: RECUPERAR SESIÓN TRAS APRETAR F5 ===
if "usuario" in st.query_params:
    st.session_state.usuario_autenticado = True
    st.session_state.email_usuario = st.query_params["usuario"]
    
    # Recuperar los créditos de Supabase al recargar la página
    if "creditos" not in st.session_state:
        try:
            respuesta_bd = supabase.table("perfiles").select("creditos").eq("email", st.session_state.email_usuario).execute()
            if len(respuesta_bd.data) > 0:
                st.session_state.creditos = respuesta_bd.data[0]["creditos"]
            else:
                st.session_state.creditos = 0
        except:
            st.session_state.creditos = 0

# 3. Pantalla de Autenticación (Modelo Freemium)
if not st.session_state.usuario_autenticado:
    st.title("🔐 Acceso a PliegoPro")
    st.write("Iniciá sesión o creá tu cuenta gratis para probar el software.")

    tab_login, tab_registro = st.tabs(["Iniciar Sesión", "Crear Cuenta"])

    with tab_login:
        email_login = st.text_input("Tu Email", key="email_login")
        password_login = st.text_input("Tu Contraseña", type="password", key="pass_login")

        if st.button("Ingresar al Software", type="primary"):
            try:
                # Inicia sesión directamente
                respuesta = supabase.auth.sign_in_with_password({"email": email_login, "password": password_login})
                st.session_state.usuario_autenticado = True
                st.session_state.email_usuario = email_login

                # === BUSCAR LOS CRÉDITOS A LA CAJA FUERTE ===
                respuesta_bd = supabase.table("perfiles").select("creditos").eq("email", email_login).execute()
                
                # Si encontró al usuario, guarda sus créditos reales en la memoria
                if len(respuesta_bd.data) > 0:
                    st.session_state.creditos = respuesta_bd.data[0]["creditos"]
                else:
                    st.session_state.creditos = 0
                
                st.rerun() # Recarga la página para que se actualice todo

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
# Ocultar elementos estéticos apuntando al botón exacto
ocultar_elementos = """
    <style>
    /* 1. Oculta exactamente el ícono/botón que encontraste */
    .stToolbarActionButtonIcon {display: none !important;}
    [data-testid="stToolbarActionButton"] {display: none !important;}
    
    /* 2. Oculta el menú de los 3 puntitos */
    #MainMenu {display: none !important;}
    
    /* 3. Vuelve el fondo de arriba transparente */
    header {background-color: transparent !important;}
    
    /* 4. Oculta la marca de agua del pie de página */
    footer {display: none !important;}
    </style>
"""
st.markdown(ocultar_elementos, unsafe_allow_html=True)
# Configuración de página
st.set_page_config(page_title="DTF / UV - Creador de Pliegos Pro", page_icon="favicon.png", layout="wide", initial_sidebar_state="expanded")
# Constantes
DPI_HIGH = 300
DPI_LOW = 72
PX_PER_CM = int(DPI_HIGH / 2.54)
SHEET_TYPES = {
    "DTF Textil (58x100 cm)": {"width_cm": 58, "height_cm": 100},
    "DTF UV (57x100 cm)": {"width_cm": 57, "height_cm": 100}
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
    if img.mode != 'RGBA': img = img.convert('RGBA')
    target_hex = target_hex.lstrip('#')
    tr, tg, tb = tuple(int(target_hex[i:i+2], 16) for i in (0, 2, 4))
    
    data = img.getdata()
    new_data = []
    for item in data:
        r, g, b, a = item
        if a > 0:
            if abs(r - tr) <= tolerance and abs(g - tg) <= tolerance and abs(b - tb) <= tolerance:
                new_data.append((r, g, b, 0)) 
            else:
                new_data.append(item)
        else:
            new_data.append(item)
            
    new_img = Image.new("RGBA", img.size)
    new_img.putdata(new_data)
    return new_img

def remove_luminance(img, lum_target, tolerance=30):
    if img.mode != 'RGBA': img = img.convert('RGBA')
    data = img.getdata()
    new_data = []
    for item in data:
        r, g, b, a = item
        if a > 0: 
            luma = int(0.299 * r + 0.587 * g + 0.114 * b)
            if abs(luma - lum_target) <= tolerance:
                new_data.append((r, g, b, 0)) 
            else:
                new_data.append(item)
        else:
            new_data.append(item)
            
    new_img = Image.new("RGBA", img.size)
    new_img.putdata(new_data)
    return new_img

# Inicializar estados de memoria
if "deleted_images" not in st.session_state: st.session_state.deleted_images = set()
if "image_history" not in st.session_state: st.session_state.image_history = {}
if "last_action_msg" not in st.session_state: st.session_state.last_action_msg = "" 

# --- LECTURA DE CRÉDITOS ---
email_usuario = st.session_state.email_usuario

respuesta_perfil = supabase.table("perfiles").select("creditos").eq("email", email_usuario).execute()
if respuesta_perfil.data:
    creditos_actuales = respuesta_perfil.data[0].get("creditos", 0)
else:
    creditos_actuales = 0

col_titulo, col_billetera = st.columns([3, 1])
with col_titulo:
    st.title("🖨️ Generador Automático de Pliegos Pro")
    st.markdown("TU SOLUCIÓN PROFESIONAL A LA PREPARACIÓN DE PLIEGOS")
with col_billetera:
    st.markdown(f"👋 Bienvenido/a, **{st.session_state.email_usuario}**")
    st.info(f"💳 **Tus Créditos: {creditos_actuales}**")
    
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
        st.markdown(f"[👉 Recargar 1 Crédito ($5.000)]({link_mp_billetera})")
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
        st.rerun()

# --- PANEL LATERAL Y CLAVES API Y FONDOS ---
edge_margin_px = cm_to_px(0.3) if use_edge_margins else 0
gang_width_px = cm_to_px(sheet_width_cm)
gang_height_px = cm_to_px(sheet_height_cm)
usable_sheet_w_px = gang_width_px - (2 * edge_margin_px)
usable_sheet_h_px = gang_height_px - (2 * edge_margin_px)

with st.sidebar:
    
    st.markdown("---")
    st.markdown("**Personalización**")
    bg_color_choice = st.selectbox("🎨 Color de fondo para recuadros:", list(BACKGROUND_COLORS.keys()), index=1)
    selected_bg_hex = BACKGROUND_COLORS[bg_color_choice]

    st.markdown("---")
    st.markdown("**Optimización de Espacio**")
    allow_rotation = st.checkbox("🔄 Permitir rotar imágenes (Tetris)", value=True, help="El sistema evaluará si rotar 90° la imagen ahorra material en el pliego.")

    st.markdown("---")
    # El visor vuelve a la barra lateral, pero con su propio botón desplegable
    with st.expander("🔍 VISOR DE VISTA PREVIA", expanded=True):
        sidebar_visor = st.empty()
        sidebar_stats = st.empty()

with col2:
    st.subheader("3. Edición de Imágenes")
    
    if uploaded_files:
        with st.expander("🛠️ Edición Masiva", expanded=False):
            b_col1, b_col2, b_col3, b_col4 = st.columns([1.5, 1, 1, 1])
            with b_col1: bulk_dim = st.radio("Ajustar todas por:", ["Ancho", "Alto"], horizontal=True, key="bulk_dim")
            with b_col2: bulk_val = st.number_input("Medida (cm)", min_value=0.1, value=5.0, step=0.5, key="bulk_val")
            with b_col3: bulk_qty = st.number_input("Cantidad c/u", min_value=1, value=1, step=1, key="bulk_qty")
            with b_col4:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("✅ Aplicar a Todas", type="primary", use_container_width=True):
                    for file in uploaded_files:
                        if file.name in st.session_state.deleted_images: continue
                        st.session_state[f"qty_{file.name}"] = bulk_qty
                        if bulk_dim == "Ancho":
                            st.session_state[f"dim_{file.name}"] = "Ancho"
                            st.session_state[f"w_{file.name}"] = float(bulk_val)
                        else:
                            st.session_state[f"dim_{file.name}"] = "Alto"
                            st.session_state[f"h_{file.name}"] = float(bulk_val)
                    st.session_state.last_action_msg = "✅ Edición masiva aplicada correctamente."
                    st.rerun()
    
    image_configs = []
    
    if uploaded_files:
        for idx, file in enumerate(uploaded_files):
            if file.name in st.session_state.deleted_images: continue
            
            if file.name not in st.session_state.image_history:
                st.session_state.image_history[file.name] = [Image.open(file)]
                
            img = st.session_state.image_history[file.name][-1]
            
            orig_w, orig_h = img.size
            aspect_ratio = orig_w / orig_h if orig_h != 0 else 1
            
            with st.expander(f"⚙️ {file.name}", expanded=False):
                
                if len(st.session_state.image_history[file.name]) > 1:
                    if st.button("↩️ Deshacer último cambio", key=f"undo_{file.name}"):
                        st.session_state.image_history[file.name].pop()
                        st.session_state.last_action_msg = f"↩️ Último cambio deshecho en {file.name}."
                        st.rerun()
                
                c_img, c_size, c_act1, c_act2 = st.columns([1, 1.5, 1, 1])
                
                with c_size:
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

                with c_img:
                    img_for_preview = get_preview_with_bg(img, selected_bg_hex)
                    st.image(img_for_preview, use_container_width=True)
                    qty = st.number_input(f"Cantidad", min_value=1, value=1, key=f"qty_{file.name}")
                    
                    if effective_dpi < 150:
                        st.warning(f"⚠️ Calidad baja: {int(effective_dpi)} DPI.")
                        if st.button("🪄 Upscale IA", key=f"up_{file.name}"):
                            with st.spinner("Mejorando resolución..."):
                                new_size = (orig_w * 2, orig_h * 2)
                                upscaled = img.resize(new_size, Image.Resampling.LANCZOS)
                                st.session_state.image_history[file.name].append(upscaled)
                                st.session_state.last_action_msg = f"🪄 Upscale aplicado correctamente a {file.name}."
                                st.rerun()
            
                            
                    if st.button("✂️ Recortar Bordes Automático", key=f"crop_{file.name}"):
                        bbox = img.getbbox()
                        if bbox:
                            new_img = img.crop(bbox)
                            st.session_state.image_history[file.name].append(new_img)
                            st.session_state.last_action_msg = f"✂️ Bordes vacíos recortados correctamente en {file.name}."
                            st.rerun()
                            
                    if st.button("🗑️ Borrar Imagen", key=f"del_{file.name}"):
                        st.session_state.deleted_images.add(file.name)
                        st.session_state.last_action_msg = f"🗑️ Imagen {file.name} borrada correctamente."
                        st.rerun()

                with c_act2:
                    st.markdown("**Avanzadas (RIP)**")
                    if st.button("🌑 Asfixia (-1px)", key=f"choke_{file.name}"):
                        new_img = apply_white_choke(img)
                        st.session_state.image_history[file.name].append(new_img)
                        st.session_state.last_action_msg = f"🌑 Asfixia aplicada correctamente a {file.name}."
                        st.rerun()
                    if st.button("⬛ Umbral", key=f"thresh_{file.name}"):
                        new_img = apply_alpha_threshold(img)
                        st.session_state.image_history[file.name].append(new_img)
                        st.session_state.last_action_msg = f"⬛ Umbral aplicado correctamente a {file.name}."
                        st.rerun()
                    
                    if "DTF UV" in sheet_choice:
                        st.markdown("**Estilo Sticker UV**")
                        s_col1, s_col2 = st.columns([1, 1])
                        with s_col1:
                            stroke_size = st.number_input("Grosor px", min_value=1, max_value=50, value=15, key=f"stroke_size_{file.name}")
                        with s_col2:
                            st.markdown("<br>", unsafe_allow_html=True)
                            if st.button("⚪ Reborde", key=f"stroke_{file.name}"):
                                new_img = apply_white_stroke(img, size=stroke_size)
                                st.session_state.image_history[file.name].append(new_img)
                                st.session_state.last_action_msg = f"⚪ Reborde blanco aplicado correctamente a {file.name}."
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
                st.markdown("**Quitar Fondos o Colores (Vista Previa en Vivo + Auto-Umbral)**")
                remove_type = st.radio("Método de borrado:", ["Gotero (Color Exacto)", "Barra (Luminosidad)"], key=f"rm_type_{file.name}", horizontal=True)

                if remove_type == "Gotero (Color Exacto)":
                    cc1, cc2 = st.columns(2)
                    with cc1:
                        target_color = st.color_picker("Color (Clica para usar el gotero)", "#000000", key=f"cp_{file.name}")
                    with cc2:
                        tol_val = st.slider("Tolerancia", 0, 100, 30, key=f"tol_exact_{file.name}")
                    
                    preview_img = remove_specific_color(img, target_color, tol_val)
                    
                    prev_col1, prev_col2 = st.columns([2, 1])
                    with prev_col1:
                        st.image(get_preview_with_bg(preview_img, selected_bg_hex), caption="Previsualización en tiempo real", use_container_width=True)
                    with prev_col2:
                        st.markdown("<br><br>", unsafe_allow_html=True)
                        if st.button("✅ Aplicar a la imagen", key=f"apply_c_{file.name}", type="primary", use_container_width=True):
                            final_img = apply_alpha_threshold(preview_img)
                            st.session_state.image_history[file.name].append(final_img)
                            st.session_state.last_action_msg = f"💧 Color eliminado (y Umbral aplicado) en {file.name}."
                            st.rerun()
                else:
                    cc1, cc2 = st.columns(2)
                    with cc1:
                        lum_val = st.slider("Tono (0=Negro, 255=Blanco)", 0, 255, 0, key=f"lum_{file.name}")
                    with cc2:
                        tol_val = st.slider("Tolerancia", 0, 100, 30, key=f"tol_lum_{file.name}")
                        
                    preview_img = remove_luminance(img, lum_val, tol_val)
                    
                    prev_col1, prev_col2 = st.columns([2, 1])
                    with prev_col1:
                        st.image(get_preview_with_bg(preview_img, selected_bg_hex), caption="Previsualización en tiempo real", use_container_width=True)
                    with prev_col2:
                        st.markdown("<br><br>", unsafe_allow_html=True)
                        if st.button("✅ Aplicar a la imagen", key=f"apply_l_{file.name}", type="primary", use_container_width=True):
                            final_img = apply_alpha_threshold(preview_img)
                            st.session_state.image_history[file.name].append(final_img)
                            st.session_state.last_action_msg = f"🌓 Tono eliminado (y Umbral aplicado) en {file.name}."
                            st.rerun()

                image_configs.append({
                    "file": file, "image": img, "qty": qty,
                    "w_px": cm_to_px(new_w_cm), "h_px": cm_to_px(new_h_cm)
                })

# --- ACTUALIZAR VISOR EN VIVO ---
if len(image_configs) > 0:
    live_packer = newPacker(mode=PackingMode.Offline, bin_algo=PackingBin.BFF, rotation=allow_rotation)
    live_packer.add_bin(usable_sheet_w_px, usable_sheet_h_px, count=1)
    
    rect_id = 0
    rect_map_live = {}
    for config in image_configs:
        for _ in range(config["qty"]):
            req_w = config["w_px"] + margin_px
            req_h = config["h_px"] + margin_px
            live_packer.add_rect(req_w, req_h, rect_id)
            rect_map_live[rect_id] = config
            rect_id += 1
            
    live_packer.pack()
    all_live_rects = live_packer.rect_list()
    
    preview_scale = 0.1 
    mini_w = int(gang_width_px * preview_scale)
    mini_h = int(gang_height_px * preview_scale)
    
    minimap = Image.new("RGBA", (mini_w, mini_h), (240, 240, 240, 255))
    draw = ImageDraw.Draw(minimap)
    
    if use_edge_margins:
        safe_x0, safe_y0 = int(edge_margin_px * preview_scale), int(edge_margin_px * preview_scale)
        safe_x1, safe_y1 = mini_w - safe_x0, mini_h - safe_y0
        draw.rectangle([safe_x0, safe_y0, safe_x1, safe_y1], outline=(200, 200, 200, 255), width=1)
    
    area_usada = 0
    for rect in all_live_rects:
        b, x, y, w, h, rid = rect
        conf = rect_map_live[rid]
        area_usada += (w * h)
        
        req_w_margin = conf["w_px"] + margin_px
        req_h_margin = conf["h_px"] + margin_px
        is_rotated = False
        if w == req_h_margin and h == req_w_margin and w != h:
            is_rotated = True
        
        px0 = int((x + edge_margin_px) * preview_scale)
        py0 = int((gang_height_px - (y + h) - edge_margin_px) * preview_scale)
        pw = int(w * preview_scale)
        ph = int(h * preview_scale)
        
        if pw > 0 and ph > 0:
            thumb_w = int(conf["w_px"] * preview_scale)
            thumb_h = int(conf["h_px"] * preview_scale)
            if thumb_w > 0 and thumb_h > 0:
                thumb = conf["image"].resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
                if thumb.mode != 'RGBA':
                    thumb = thumb.convert('RGBA')
                
                if is_rotated:
                    thumb = thumb.rotate(90, expand=True)
                
                minimap.paste(thumb, (px0, py0), thumb)
                draw.rectangle([px0, py0, px0 + pw, py0 + ph], outline=(50, 100, 200, 100), width=1)
        
    sidebar_visor.image(minimap, use_container_width=True)
    
    area_total = usable_sheet_w_px * usable_sheet_h_px
    if len(all_live_rects) < rect_id:
        sidebar_stats.error(f"¡Rebasaste al Pliego 2! {rect_id - len(all_live_rects)} ítems fuera.")
    else:
        sidebar_stats.success(f"Espacio usado: {(area_usada / area_total) * 100:.1f}%")

# 6. Generador Final
if uploaded_files and len(image_configs) > 0:
    st.markdown("---")
   # 6. Generador Final
if uploaded_files and len(image_configs) > 0:
    st.markdown("---")
    
    # 1. Creamos la memoria
    if "proceso_iniciado" not in st.session_state:
        st.session_state.proceso_iniciado = False
        
    # 2. El botón ahora solo enciende la memoria
    if st.button("🚀 Generar Archivos Finales", type="primary", use_container_width=True):
        st.session_state.proceso_iniciado = True
        
    # 3. Todo tu código pasa a depender de la memoria
    if st.session_state.proceso_iniciado:
        with st.spinner("Procesando pliegos de impresión estricta..."):
            
            packer = newPacker(mode=PackingMode.Offline, bin_algo=PackingBin.BFF, rotation=allow_rotation)
            packer.add_bin(usable_sheet_w_px, usable_sheet_h_px, count=20)
            
            rect_id = 0
            rect_map = {} 
            for config in image_configs:
                for _ in range(config["qty"]):
                    req_w = config["w_px"] + margin_px
                    req_h = config["h_px"] + margin_px
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
                    
                    req_w_margin = conf["w_px"] + margin_px
                    req_h_margin = conf["h_px"] + margin_px
                    is_rotated = False
                    if w == req_h_margin and h == req_w_margin and w != h:
                        is_rotated = True
                    
                    resized_img = conf["image"].resize((conf["w_px"], conf["h_px"]), Image.Resampling.LANCZOS)
                    if resized_img.mode != 'RGBA': resized_img = resized_img.convert('RGBA')

                    if is_rotated:
                        resized_img = resized_img.rotate(90, expand=True)

                    paste_x = x + edge_margin_px
                    paste_y = gang_height_px - (y + h) - edge_margin_px
                    gang_high_res.paste(resized_img, (paste_x, paste_y), resized_img)
                
                high_filename = os.path.join(folder_name, f"pliego_{i+1}_alta.png")
                gang_high_res.save(high_filename, format='PNG', dpi=(DPI_HIGH, DPI_HIGH))
                gang_files_high.append(high_filename)
                
                scale_factor = DPI_LOW / DPI_HIGH
                prev_w, prev_h = int(gang_width_px * scale_factor), int(gang_height_px * scale_factor)
                
                preview_sheet = Image.new("RGBA", (prev_w, prev_h), MUESTRA_BG_COLOR)
                final_sheet_low = gang_high_res.resize((prev_w, prev_h), Image.Resampling.LANCZOS)
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
                        # Restamos los créditos en Supabase
                        nuevos_creditos = creditos_actuales - cantidad_pliegos
                        supabase.table("perfiles").update({"creditos": nuevos_creditos}).eq("email", email_usuario).execute()
                        st.session_state.pliegos_desbloqueados = True
                        st.rerun() # Recargamos para mostrar el botón de descarga
                else:
                    st.error("❌ No tenés créditos suficientes.")
                    
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
