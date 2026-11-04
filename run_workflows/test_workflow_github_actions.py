# gh auth login
# python test_workflow_github_actions.py unir_imagenes_videos_audios.json
# python test_workflow_github_actions.py agregar_logo_a_video.json

import json
import subprocess
import sys

# Seleccionar archivo de configuración
config_path = sys.argv[1]

# Leer configuración
with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

# Construir inputs para GitHub
inputs = {
    key: json.dumps(value) if isinstance(value, (dict, list)) else str(value)
    for key, value in config["inputs"].items()
}

# Mostrar un resumen claro de lo que se va a ejecutar.
print("\n" + "=" * 60)
print("🚀 Inicio de GitHub Actions")
print(f"Workflow : {config['workflow']}")
print(f"Rama     : {config['branch']}")
print("Parámetros:")

# JSON con sangría para que los objetos y listas se vean ordenados.
print(json.dumps(inputs, indent=2, ensure_ascii=False))
print("=" * 60 + "\n")

# Construir comando
command = [
    "gh",
    "workflow",
    "run",
    config["workflow"],
    "--ref",
    config["branch"],
    "--json"
]

# Ejecutar workflow
result = subprocess.run(
    command,
    input=json.dumps(inputs),
    text=True
)

sys.exit(result.returncode)