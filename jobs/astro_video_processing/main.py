import argparse
import json
import os
from pathlib import Path

from agregar_logo_a_video import agregar_logo
from unir_imagenes_videos_audios import cargar_elementos, crear_video


def leer_argumentos():
    parser = argparse.ArgumentParser(
        description="Procesa tareas de video con FFmpeg."
    )

    parser.add_argument(
        "--modo",
        required=True,
        choices=["agregar_logo", "unir_vid_img_aud"],
        help="Tipo de proceso que se ejecutará.",
    )

    grupo_tasks = parser.add_mutually_exclusive_group()
    grupo_tasks.add_argument(
        "--tasks-json",
        help="Ruta al JSON que contiene la lista de tareas.",
    )
    grupo_tasks.add_argument(
        "--tasks",
        help="Lista de tareas escrita como una cadena JSON.",
    )

    return parser.parse_args()


def cargar_configuracion(args):
    if args.tasks_json:
        with open(args.tasks_json, "r", encoding="utf-8") as archivo:
            tareas = json.load(archivo)["tasks"]

    elif args.tasks:
        posible_ruta = Path(args.tasks)

        if posible_ruta.is_file():
            with posible_ruta.open("r", encoding="utf-8") as archivo:
                tareas = json.load(archivo)["tasks"]
        else:
            tareas = json.loads(args.tasks)["tasks"]

    else:
        raise ValueError(
            "Indica --tasks-json ó --tasks"
        )

    indice = int(os.environ.get("CLOUD_RUN_TASK_INDEX", "0"))

    return tareas[indice]


def ejecutar():
    args = leer_argumentos()
    config = cargar_configuracion(args)

    if args.modo == "agregar_logo":
        agregar_logo(config)

    elif args.modo == "unir_vid_img_aud":
        elementos = cargar_elementos(config["elementos"])

        crear_video(
            elementos=elementos,
            audio=config.get("audio"),
            inicio_audio=config.get("inicio_audio", 0),
            salida=config.get("salida"),
            fps=config.get("fps", 24),
        )


if __name__ == "__main__":
    ejecutar()