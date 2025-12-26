# 🧠 **SISTEMA DE VISIÓN ARTIFICIAL Y CONTROL**

Sistema de visión artificial y control desarrollado con **FastAPI, OpenCV, MediaPipe y cámaras ONVIF**.

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
```

---

# 🧪 **2️⃣ CREAR Y ACTIVAR EL ENTORNO VIRTUAL**

Crear el entorno virtual:

```bash
python -m venv venv
```

Activarlo:

```bash
venv\Scripts\activate
```

---

# 📚 **3️⃣ INSTALAR DEPENDENCIAS**

Instalar librerías de ejecución (runtime):

```bash
pip install -r requirements.txt
```

Instalar herramientas de desarrollo y build:

```bash
pip install -r requirements-dev.txt
```

---

# ▶️ **4️⃣ EJECUTAR EN MODO DESARROLLO**

Ejecutar la aplicación principal:

```bash
python run_ui.py
```

---

# 🧪 **5️⃣ DESARROLLO**

Durante el desarrollo puedes:

- Editar el código
- Ejecutar el servidor o el script principal
- Usar `pipreqs`, `pip-check-reqs` y `pip-tools` para validar dependencias

Verificar imports faltantes:

```bash
pip-missing-reqs .
```

---

# 🏗 **6️⃣ GENERAR EL EJECUTABLE (BUILD)**

Cuando el desarrollo esté terminado:

```bash
pyinstaller run.spec
```

El ejecutable final se generará en:

```text
/dist/
```

---

# 📦 **7️⃣ DISTRIBUCIÓN**

El contenido de la carpeta:

```text
dist/
```

- Es el que se debe distribuir o instalar en las máquinas destino  
- No es necesario que esas máquinas tengan Python instalado  

---

# 🛡 **NOTAS IMPORTANTES**

- Nunca ejecutes **PyInstaller** fuera del entorno virtual
- No uses `pip freeze > requirements.txt` en este proyecto
- Las dependencias de runtime y desarrollo están separadas por diseño:
  - `requirements.txt` → lo que el ejecutable necesita  
  - `requirements-dev.txt` → herramientas para construirlo  

---
