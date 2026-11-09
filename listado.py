import argparse
import json
from pathlib import Path


def crear_listado(directorio: Path) -> dict:
	listado = {}

	for archivo in sorted(directorio.rglob("*")):
		if archivo.is_file():
			carpeta = str(archivo.parent.relative_to(directorio)) or "."
			listado.setdefault(carpeta, []).append(
				{"nombre": archivo.name, "tamano_bytes": archivo.stat().st_size}
			)

	return listado


def main() -> None:
	parser = argparse.ArgumentParser(
		description="Lista en JSON los archivos de un directorio y sus subdirectorios."
	)
	parser.add_argument("directorio", nargs="?", help="Directorio que se va a listar")
	args = parser.parse_args()

	ruta = Path(args.directorio or input("Introduce el directorio: ")).expanduser()
	if not ruta.is_dir():
		parser.error(f"El directorio no existe o no es válido: {ruta}")

	archivo_salida = Path("listado.json")
	archivo_salida.write_text(
		json.dumps(crear_listado(ruta.resolve()), ensure_ascii=False, indent=2),
		encoding="utf-8",
	)
	print(f"Listado guardado en: {archivo_salida.resolve()}")


if __name__ == "__main__":
	main()
