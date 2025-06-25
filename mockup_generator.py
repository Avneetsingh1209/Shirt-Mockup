import streamlit as st
from PIL import Image
import numpy as np
import zipfile
import io
import cv2
import os

st.set_page_config(page_title="Shirt Mockup Generator", layout="centered")
st.title("👕 Shirt Mockup Generator – Live Preview + ZIP Export")

st.markdown("""
Upload multiple design PNGs and shirt templates.  
Adjust placement sliders and instantly preview every combination!
""")

# --- Sliders in Sidebar ---
plain_padding_ratio = st.sidebar.slider("Padding – Plain Shirt", 0.1, 1.0, 0.45, 0.05)
model_padding_ratio = st.sidebar.slider("Padding – Model Shirt", 0.1, 1.0, 0.35, 0.05)
plain_offset_pct = st.sidebar.slider("Vertical Offset – Plain Shirt (%)", -50, 100, -7, 1)
model_offset_pct = st.sidebar.slider("Vertical Offset – Model Shirt (%)", -50, 100, 3, 1)

# --- Session State Init ---
if "zip_data" not in st.session_state:
    st.session_state.zip_data = None

# --- Upload Sections ---
design_files = st.file_uploader("📌 Upload Designs (PNG/JPG)", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
shirt_files = st.file_uploader("🎨 Upload Shirt Templates", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

# --- Utility: Auto Bounding Box ---
def get_shirt_bbox(pil_image):
    img_cv = np.array(pil_image.convert("RGB"))[:, :, ::-1]
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blurred, 240, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        largest = max(contours, key=cv2.contourArea)
        return cv2.boundingRect(largest)
    return None

# --- Process + Preview ---
if design_files and shirt_files:
    st.markdown("## 👀 Live Preview – All Designs × All Shirts")

    previews = []
    all_outputs = []

    for design_file in design_files:
        design_name = os.path.splitext(design_file.name)[0]
        design = Image.open(design_file).convert("RGBA")

        for shirt_file in shirt_files:
            shirt_name = os.path.splitext(shirt_file.name)[0]
            shirt = Image.open(shirt_file).convert("RGBA")

            is_model = "model" in shirt_file.name.lower()
            offset_pct = model_offset_pct if is_model else plain_offset_pct
            padding_ratio = model_padding_ratio if is_model else plain_padding_ratio

            bbox = get_shirt_bbox(shirt)
            if bbox:
                sx, sy, sw, sh = bbox
                scale = min(sw / design.width, sh / design.height, 1.0) * padding_ratio
                new_width = int(design.width * scale)
                new_height = int(design.height * scale)
                resized = design.resize((new_width, new_height))

                y_offset = int(sh * offset_pct / 100)
                x = sx + (sw - new_width) // 2
                y = sy + y_offset
            else:
                resized = design
                x = (shirt.width - resized.width) // 2
                y = (shirt.height - resized.height) // 2

            shirt_copy = shirt.copy()
            shirt_copy.paste(resized, (x, y), resized)
            previews.append((f"{design_name} + {shirt_name}", shirt_copy))

            # Save to buffer
            output_name = f"{design_name}_{shirt_name}.png"
            img_buffer = io.BytesIO()
            shirt_copy.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            all_outputs.append((output_name, img_buffer.read()))

    # Display all previews
    for name, img in previews:
        st.image(img, caption=name, use_container_width=True)

    # ZIP All Outputs
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for filename, data in all_outputs:
            zipf.writestr(filename, data)
    zip_buffer.seek(0)
    st.session_state.zip_data = zip_buffer

# --- Download ZIP ---
if st.session_state.zip_data:
    st.download_button(
        label="📦 Download All Mockups (ZIP)",
        data=st.session_state.zip_data,
        file_name="all_mockups.zip",
        mime="application/zip"
    )
