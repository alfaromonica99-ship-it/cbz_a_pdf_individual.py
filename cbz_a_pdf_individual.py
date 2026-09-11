import streamlit as st
from pathlib import Path
import tempfile
import zipfile
import rarfile
import re
import img2pdf
import subprocess
from PIL import Image

#Abrir zip streamlit

import shutil

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
}


def natural_key(path):
    return [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", str(path))
    ]


def extract_cbz(comic_path, output_dir):
    with zipfile.ZipFile(comic_path, "r") as archive:
        archive.extractall(output_dir)


def extract_cbr(input_file, output_dir):
    import shutil

    # Busca automáticamente 7-Zip según el sistema operativo
    seven_zip = (
        shutil.which("7z")
        or shutil.which("7zz")
        or shutil.which("7za")
    )

    # Si estamos en Windows y no está en PATH
    if not seven_zip:
        windows_7zip = r"C:\Program Files\7-Zip\7z.exe"

        if Path(windows_7zip).exists():
            seven_zip = windows_7zip

    if not seven_zip:
        raise RuntimeError(
            "No se encontró 7-Zip en el sistema."
        )

    subprocess.run(
        [
            seven_zip,
            "x",
            str(input_file),
            f"-o{output_dir}",
            "-y"
        ],
        check=True
    )


def find_images(folder):
    images = []

    for file in Path(folder).rglob("*"):
        if file.is_file() and file.suffix.lower() in IMAGE_EXTENSIONS:
            images.append(file)

    images.sort(key=natural_key)

    return images


def prepare_images(images, work_dir):
    """
    Conserva JPG y PNG tal como vienen.
    Convierte WEBP/BMP/TIFF a PNG sin compresión con pérdida.
    """

    final_images = []

    converted_folder = Path(work_dir) / "converted"
    converted_folder.mkdir(exist_ok=True)

    for index, image_path in enumerate(images):

        extension = image_path.suffix.lower()

        if extension in {".jpg", ".jpeg", ".png"}:
            final_images.append(image_path)
            continue

        converted_path = (
            converted_folder / f"{index:06d}.png"
        )

        with Image.open(image_path) as image:

            if image.mode not in ("RGB", "RGBA", "L"):
                image = image.convert("RGB")

            image.save(
                converted_path,
                format="PNG",
                optimize=False
            )

        final_images.append(converted_path)

    return final_images


def create_pdf(images):
    image_paths = [str(image) for image in images]

    return img2pdf.convert(image_paths)


# ---------------------------------------------------------
# STREAMLIT
# ---------------------------------------------------------

st.set_page_config(
    page_title="Comic → PDF",
    page_icon="📚",
    layout="centered"
)

st.title("📚 Comic → PDF")

st.write(
    """
    Convierte archivos **CBZ** o **CBR** a PDF conservando
    la máxima calidad posible de las imágenes.
    """
)

uploaded_file = st.file_uploader(
    "Selecciona un comic",
    type=["cbz", "cbr"]
)


if uploaded_file is not None:

    extension = Path(uploaded_file.name).suffix.lower()

    st.success(
        f"Archivo cargado: {uploaded_file.name}"
    )

    with tempfile.TemporaryDirectory() as temp:

        temp_dir = Path(temp)

        comic_path = temp_dir / uploaded_file.name

        # Guardar archivo temporal
        with open(comic_path, "wb") as file:
            file.write(uploaded_file.getbuffer())

        extract_folder = temp_dir / "comic"
        extract_folder.mkdir()

        # --------------------------------------------------
        # EXTRAER
        # --------------------------------------------------

        try:

            with st.spinner("Extrayendo comic..."):

                if extension == ".cbz":
                    extract_cbz(
                        comic_path,
                        extract_folder
                    )

                elif extension == ".cbr":
                    extract_cbr(
                        comic_path,
                        extract_folder
                    )

        except Exception as e:

            st.error(
                f"Error extrayendo el archivo:\n\n{e}"
            )

            st.stop()

        # --------------------------------------------------
        # BUSCAR IMÁGENES
        # --------------------------------------------------

        images = find_images(extract_folder)

        if not images:

            st.error(
                "No se encontraron imágenes dentro del comic."
            )

            st.stop()

        st.metric(
            "Páginas encontradas",
            len(images)
        )

        # --------------------------------------------------
        # PREVIEW
        # --------------------------------------------------

        st.subheader("Vista previa")

        preview_count = min(
            6,
            len(images)
        )

        columns = st.columns(3)

        for index in range(preview_count):

            with columns[index % 3]:

                st.image(
                    str(images[index]),
                    caption=f"Página {index + 1}",
                    use_container_width=True
                )

        # --------------------------------------------------
        # CONVERTIR
        # --------------------------------------------------

        if st.button(
            "🚀 Convertir a PDF",
            type="primary",
            use_container_width=True
        ):

            try:

                progress = st.progress(0)

                status = st.empty()

                status.text(
                    "Preparando imágenes..."
                )

                progress.progress(25)

                final_images = prepare_images(
                    images,
                    temp_dir
                )

                progress.progress(60)

                status.text(
                    "Creando PDF..."
                )

                pdf_bytes = create_pdf(
                    final_images
                )

                progress.progress(100)

                status.text(
                    "PDF terminado"
                )

                output_name = (
                    Path(uploaded_file.name).stem
                    + ".pdf"
                )

                st.success(
                    "Conversión completada"
                )

                file_size = (
                    len(pdf_bytes)
                    / 1024
                    / 1024
                )

                st.write(
                    f"**Tamaño del PDF:** "
                    f"{file_size:.2f} MB"
                )

                st.download_button(
                    label="⬇️ Descargar PDF",
                    data=pdf_bytes,
                    file_name=output_name,
                    mime="application/pdf",
                    use_container_width=True
                )

            except Exception as e:

                st.error(
                    f"Error creando el PDF:\n\n{e}"
                )
