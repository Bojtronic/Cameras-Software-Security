# 🧠 **SISTEMA DE VISIÓN ARTIFICIAL Y CONTROL**

Sistema de visión artificial y control desarrollado con FastAPI, OpenCV, MediaPipe y cámaras ONVIF.

---

# 📦 **REQUISITOS PREVIOS**

- ✅ **Python 3.10 o superior**  
- ✅ **Git**  
- ✅ **Windows 10/11** (requerido para generar el `.exe`)  

---



# 📥 **1️⃣ CLONAR EL REPOSITORIO**

```bash
git clone https://github.com/Bojtronic/Cameras-Software-Security.git
cd Cameras-Software-Security




# 🧪 **2️⃣  Crear y activar el entorno virtual**

Crear el entorno virtual:

python -m venv venv

Activarlo:

venv\Scripts\activate



# 📚 **3️⃣ Instalar dependencias**

Instalar librerías de ejecución (runtime):

pip install -r requirements.txt

Instalar herramientas de desarrollo y build:

pip install -r requirements-dev.txt



# ▶️ **4️⃣ Ejecutar en modo desarrollo**

Ejecutar la aplicación principal:

python run_ui.py



# 🧪 **5️⃣ Desarrollo**

Durante el desarrollo puedes:

- Editar el código

- Ejecutar el servidor o el script principal

- Usar pipreqs, pip-check-reqs y pip-tools para validar dependencias

- Verificar imports faltantes:

pip-missing-reqs .




# 🏗 **6️⃣ Generar el ejecutable (build)**

Cuando el desarrollo esté terminado:

pyinstaller run.spec

El ejecutable final se generará en:

/dist/


# 📦 **7️⃣ Distribución**

El contenido de la carpeta:

dist/

- es el que se debe distribuir o instalar en las máquinas destino.
- No es necesario que esas máquinas tengan Python instalado.



# 🛡 **Notas importantes**

- Nunca ejecutes PyInstaller fuera del entorno virtual.

- No uses pip freeze > requirements.txt en este proyecto.

- Las dependencias de runtime y desarrollo están separadas por diseño.

- requirements.txt define lo que el ejecutable necesita.

- requirements-dev.txt define las herramientas para construirlo.

