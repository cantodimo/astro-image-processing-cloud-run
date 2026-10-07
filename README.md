# 🌌 Astro Image Processing

Servicio de procesamiento de imágenes desarrollado para un caso de uso específico personal de fotos de astronomia

La aplicación proporciona una API para realizar diferentes procesos sobre imágenes y utiliza **Google Cloud** como infraestructura de ejecución y almacenamiento.

---

## 🏗️ Arquitectura

```text
                    ┌─────────────────┐
                    │     GitHub      │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ GitHub Actions  │
                    │                 │
                    │ Tests / Build   │
                    │ / Deploy        │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │    Artifact     │
                    │    Registry     │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │    Cloud Run    │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Cloud Storage   │
                    └─────────────────┘
```

La infraestructura de Google Cloud se administra mediante **Terraform**.

---

## ✨ Funcionalidades

* 🖼️ Agregar logos a imágenes.
* ✏️ Agregar texto a imágenes.
* 🧪 Pruebas funcionales y de integración con **pytest**.
* 🚀 Automatización de pruebas y despliegue mediante **GitHub Actions**.

---

## 📁 Estructura del proyecto

```text
astro-image-processing-cloud-run/
│
├── servicios/
│   └── astro_image_processing/
│       ├── app.py
│       ├── Dockerfile
│       ├── requirements.txt
│       └── py_processing/
│
├── tests/
│   └── astro_image_processing/
│       ├── test_logo.py
│       ├── test_texto.py
│       └── test_integracion.py
│
├── terraform/
│   ├── infra/
│   └── deploy/
│
├── .github/
│   └── workflows/
│
│
└── README.md
```

---

## 🛠️ Tecnologías

| Tecnología            | Uso                       |
| --------------------- | ------------------------- |
| **Python / Flask**    | API y procesamiento       |
| **Pillow / NumPy**    | Procesamiento de imágenes |
| **pytest**            | Pruebas                   |
| **Docker**            | Contenedorización         |
| **GitHub Actions**    | Automatización            |
| **Google Cloud Run**  | Ejecución del servicio    |
| **Cloud Storage**     | Almacenamiento            |
| **Artifact Registry** | Imágenes Docker           |
| **Terraform**         | Infraestructura           |

---

## 🔐 Autenticación

GitHub Actions utiliza **Workload Identity Federation** para acceder a Google Cloud sin almacenar claves privadas de cuentas de servicio en GitHub.

---

## ☁️ Google Cloud

El servicio se ejecuta en **Cloud Run**, utilizando una imagen almacenada en **Artifact Registry** y archivos almacenados en **Cloud Storage** usando Cloud Storage volume mount.

La infraestructura se define y administra mediante **Terraform**.

---

## 📌 Estado

Proyecto en desarrollo.
