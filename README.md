# 🧠 SISTEMA DE VISIÓN ARTIFICIAL Y CONTROL

Sistema de visión artificial y control desarrollado con **FastAPI, OpenCV, MediaPipe y cámaras ONVIF**, con clasificación de poses mediante **IA (ONNX Runtime)**.

---

## 📦 Requisitos

- **Python 3.10+**
- **Git**
- **Windows 10/11** (para generar `.exe`)

---

## 📥 1. Clonar repositorio

```bash
git clone https://github.com/Bojtronic/Cameras-Software-Security.git
cd Cameras-Software-Security
```

---

## 🧪 2. Entornos virtuales

Se usan **dos entornos**:

| Entorno | Uso |
|-------|-----|
| `venv-train` | Crear dataset, entrenar modelo, exportar a ONNX |
| `venv` | Ejecutar FastAPI, MediaPipe y generar ejecutable |

Crear entornos:

```bash
python -m venv venv-train
python -m venv venv
```

---

## 📚 3. Instalar dependencias

### 🔹 Entrenamiento IA

```bash
venv-train\Scripts\activate
pip install -r requirements-train.txt
deactivate
```

### 🔹 Desarrollo y runtime

```bash
venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

---

## 🧠 4. Flujo del modelo IA

1. **Recolectar dataset** (pose_dataset.csv)
2. **Entrenar modelo** → genera `pose_model.h5`
3. **Convertir a ONNX**
4. **Usar ONNX en producción**

### Convertir Keras → ONNX

```bash
python -m tf2onnx.convert \
  --keras pose_model.h5 \
  --output models/pose_model.onnx \
  --opset 13
```

⚠ **Solo el `.onnx` se usa en producción**.  
TensorFlow **NO** es requerido en `venv`.

---

## ▶️ 5. Ejecutar en desarrollo

```bash
venv\Scripts\activate
python run_ui.py
```

---

## 🏗 6. Generar ejecutable

```bash
pyinstaller run.spec
```

El `.exe` final queda en:

```text
/dist/
```

---

## 📦 7. Distribución

La carpeta:

```text
dist/
```

- Contiene el ejecutable y dependencias
- No requiere Python instalado

---

## 🛡 Notas importantes

- **No mezclar entornos**
- **TensorFlow solo vive en `venv-train`**
- El runtime usa **ONNX Runtime**
- `requirements.txt` = producción
- `requirements-dev.txt` = build
- `requirements-train.txt` = IA
