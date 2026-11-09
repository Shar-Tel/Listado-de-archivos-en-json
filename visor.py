import json
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


@dataclass(frozen=True)
class Archivo:
	"""Representa un archivo del listado y la carpeta donde se encuentra."""

	carpeta: str
	nombre: str
	tamano_bytes: int


def cargar_listado(ruta: Path) -> list[Archivo]:
	"""Lee y valida el JSON generado por listado.py."""
	try:
		contenido = json.loads(ruta.read_text(encoding="utf-8"))
	except json.JSONDecodeError as error:
		raise ValueError(f"El archivo no contiene un JSON válido: {error}") from error

	# listado.py organiza los datos como {carpeta: [{nombre, tamano_bytes}, ...]}.
	if not isinstance(contenido, dict):
		raise ValueError("El contenido debe ser un objeto JSON agrupado por carpetas.")

	archivos = []
	for carpeta, elementos in contenido.items():
		if not isinstance(carpeta, str) or not isinstance(elementos, list):
			raise ValueError("Cada carpeta debe contener una lista de archivos.")

		for elemento in elementos:
			if not isinstance(elemento, dict):
				raise ValueError(f"Hay una entrada de archivo no válida en «{carpeta}».")

			nombre = elemento.get("nombre")
			tamano = elemento.get("tamano_bytes")
			# bool es una subclase de int en Python, pero no es un tamaño válido.
			if (
				not isinstance(nombre, str)
				or not isinstance(tamano, int)
				or isinstance(tamano, bool)
				or tamano < 0
			):
				raise ValueError(f"Hay un archivo con nombre o tamaño no válido en «{carpeta}».")

			archivos.append(Archivo(carpeta, nombre, tamano))

	return archivos


def formato_tamano(tamano: int) -> str:
	"""Convierte bytes a una unidad legible sin perder el valor original."""
	unidades = ("B", "KB", "MB", "GB", "TB")
	valor = float(tamano)
	for unidad in unidades:
		if valor < 1024 or unidad == unidades[-1]:
			if unidad == "B":
				return f"{int(valor):,} {unidad}"
			return f"{valor:,.1f} {unidad}"
		valor /= 1024
	return f"{tamano:,} B"


class VisorArchivos:
	"""Construye y mantiene la ventana gráfica del visor."""

	def __init__(self, raiz: tk.Tk) -> None:
		self.raiz = raiz
		# Estado que comparten los controles: listado, carpeta, búsqueda y orden.
		self.archivos: list[Archivo] = []
		self.ruta_listado: Path | None = None
		self.carpeta_seleccionada = "."
		self.columna_orden = "nombre"
		self.orden_inverso = False
		self.busqueda = tk.StringVar()

		raiz.title("Visor de listados de archivos")
		raiz.geometry("1100x700")
		raiz.minsize(760, 480)
		self._configurar_estilo()
		self._crear_interfaz()
		# Actualiza la tabla cada vez que cambia el texto de búsqueda.
		self.busqueda.trace_add("write", lambda *_: self._actualizar_archivos())

		# Facilita el primer uso cuando el JSON generado está junto a este programa.
		listado_inicial = Path(__file__).with_name("listado.json")
		if listado_inicial.is_file():
			self._cargar_archivo(listado_inicial)

	def _configurar_estilo(self) -> None:
		estilo = ttk.Style(self.raiz)
		if "clam" in estilo.theme_names():
			estilo.theme_use("clam")
		estilo.configure("Titulo.TLabel", font=("", 18, "bold"))
		estilo.configure("Resumen.TLabel", font=("", 10))
		estilo.configure("Treeview", rowheight=27)
		estilo.configure("Treeview.Heading", font=("", 10, "bold"))

	def _crear_interfaz(self) -> None:
		contenedor = ttk.Frame(self.raiz, padding=18)
		contenedor.pack(fill="both", expand=True)
		contenedor.columnconfigure(0, weight=1)
		contenedor.rowconfigure(2, weight=1)

		# Cabecera con el resumen actual y el selector de otro listado.
		cabecera = ttk.Frame(contenedor)
		cabecera.grid(row=0, column=0, sticky="ew", pady=(0, 14))
		cabecera.columnconfigure(0, weight=1)
		ttk.Label(cabecera, text="Visor de archivos", style="Titulo.TLabel").grid(
			row=0, column=0, sticky="w"
		)
		self.etiqueta_resumen = ttk.Label(cabecera, text="Abre un listado JSON para empezar", style="Resumen.TLabel")
		self.etiqueta_resumen.grid(row=1, column=0, sticky="w", pady=(4, 0))
		ttk.Button(cabecera, text="Abrir listado…", command=self._elegir_listado).grid(
			row=0, column=1, rowspan=2, padx=(12, 0)
		)

		# La búsqueda se aplica a nombres de archivo y rutas de carpeta.
		barra_busqueda = ttk.Frame(contenedor)
		barra_busqueda.grid(row=1, column=0, sticky="ew", pady=(0, 12))
		ttk.Label(barra_busqueda, text="Buscar").pack(side="left", padx=(0, 8))
		campo_busqueda = ttk.Entry(barra_busqueda, textvariable=self.busqueda)
		campo_busqueda.pack(side="left", fill="x", expand=True)
		ttk.Label(barra_busqueda, text="  en nombre y carpeta").pack(side="left")

		# Los paneles laterales pueden redimensionarse arrastrando el separador.
		paneles = ttk.Panedwindow(contenedor, orient="horizontal")
		paneles.grid(row=2, column=0, sticky="nsew")
		panel_carpetas = ttk.Frame(paneles, padding=(0, 0, 12, 0))
		panel_archivos = ttk.Frame(paneles)
		paneles.add(panel_carpetas, weight=1)
		paneles.add(panel_archivos, weight=4)
		panel_carpetas.rowconfigure(1, weight=1)
		panel_carpetas.columnconfigure(0, weight=1)
		panel_archivos.rowconfigure(1, weight=1)
		panel_archivos.columnconfigure(0, weight=1)

		ttk.Label(panel_carpetas, text="Carpetas").grid(row=0, column=0, sticky="w", pady=(0, 6))
		self.arbol_carpetas = ttk.Treeview(
			panel_carpetas, columns=("cantidad",), show="tree headings", selectmode="browse"
		)
		self.arbol_carpetas.heading("#0", text="Nombre")
		self.arbol_carpetas.heading("cantidad", text="Archivos")
		self.arbol_carpetas.column("#0", width=170, minwidth=100)
		self.arbol_carpetas.column("cantidad", width=65, minwidth=55, anchor="e")
		self.arbol_carpetas.grid(row=1, column=0, sticky="nsew")
		scroll_carpetas = ttk.Scrollbar(
			panel_carpetas, orient="vertical", command=self.arbol_carpetas.yview
		)
		scroll_carpetas.grid(row=1, column=1, sticky="ns")
		self.arbol_carpetas.configure(yscrollcommand=scroll_carpetas.set)
		self.arbol_carpetas.bind(
			"<<TreeviewSelect>>", lambda *_: self._seleccionar_carpeta()
		)

		ttk.Label(panel_archivos, text="Archivos").grid(row=0, column=0, sticky="w", pady=(0, 6))
		self.tabla_archivos = ttk.Treeview(
			panel_archivos,
			columns=("nombre", "carpeta", "tamano"),
			show="headings",
			selectmode="browse",
		)
		self.tabla_archivos.heading("nombre", text="Nombre", command=lambda: self._ordenar("nombre"))
		self.tabla_archivos.heading("carpeta", text="Carpeta", command=lambda: self._ordenar("carpeta"))
		self.tabla_archivos.heading("tamano", text="Tamaño", command=lambda: self._ordenar("tamano"))
		self.tabla_archivos.column("nombre", width=480, minwidth=180)
		self.tabla_archivos.column("carpeta", width=190, minwidth=100)
		self.tabla_archivos.column("tamano", width=105, minwidth=90, anchor="e")
		self.tabla_archivos.grid(row=1, column=0, sticky="nsew")
		scroll_archivos = ttk.Scrollbar(
			panel_archivos, orient="vertical", command=self.tabla_archivos.yview
		)
		scroll_archivos.grid(row=1, column=1, sticky="ns")
		self.tabla_archivos.configure(yscrollcommand=scroll_archivos.set)

		self.etiqueta_estado = ttk.Label(contenedor, text="", anchor="w")
		self.etiqueta_estado.grid(row=3, column=0, sticky="ew", pady=(10, 0))

	def _elegir_listado(self) -> None:
		"""Muestra el selector de archivos y carga la selección del usuario."""
		ruta = filedialog.askopenfilename(
			title="Abrir listado de archivos",
			filetypes=(("Archivos JSON", "*.json"), ("Todos los archivos", "*.*")),
			initialdir=str(self.ruta_listado.parent) if self.ruta_listado else None,
		)
		if ruta:
			self._cargar_archivo(Path(ruta))

	def _cargar_archivo(self, ruta: Path) -> None:
		"""Reemplaza el listado visible solo si el archivo se pudo validar."""
		try:
			archivos = cargar_listado(ruta)
		except (OSError, UnicodeError, ValueError) as error:
			messagebox.showerror("No se pudo abrir el listado", str(error), parent=self.raiz)
			return

		self.archivos = archivos
		self.ruta_listado = ruta
		self.carpeta_seleccionada = "."
		self.busqueda.set("")
		self._actualizar_arbol()
		self._actualizar_archivos()
		self._actualizar_resumen()

	def _actualizar_arbol(self) -> None:
		"""Reconstruye el árbol e incluye en cada carpeta sus archivos descendientes."""
		carpetas_existentes = self.arbol_carpetas.get_children()
		if carpetas_existentes:
			self.arbol_carpetas.delete(*carpetas_existentes)
		raiz_id = "carpeta:."
		self.arbol_carpetas.insert("", "end", iid=raiz_id, text="Todas las carpetas", values=(len(self.archivos),))

		conteos: dict[str, int] = {}
		etiquetas: dict[str, str] = {}
		for archivo in self.archivos:
			# Normaliza separadores para mostrar JSON de distintos sistemas operativos.
			carpeta = archivo.carpeta.replace("\\", "/").strip("/")
			if not carpeta or carpeta == ".":
				continue
			partes = carpeta.split("/")
			for indice, parte in enumerate(partes):
				ruta = "/".join(partes[: indice + 1])
				etiquetas[ruta] = parte
				conteos[ruta] = conteos.get(ruta, 0) + 1

		rutas = sorted(etiquetas, key=lambda ruta: (ruta.count("/"), ruta.casefold()))
		for ruta in rutas:
			padre = ruta.rpartition("/")[0] or "."
			padre_id = f"carpeta:{padre}"
			self.arbol_carpetas.insert(
				padre_id,
				"end",
				iid=f"carpeta:{ruta}",
				text=etiquetas[ruta],
				values=(conteos[ruta],),
			)

		self.arbol_carpetas.item(raiz_id, open=True)
		self.arbol_carpetas.selection_set(raiz_id)
		self.arbol_carpetas.focus(raiz_id)

	def _seleccionar_carpeta(self) -> None:
		seleccion = self.arbol_carpetas.selection()
		if seleccion:
			self.carpeta_seleccionada = seleccion[0].removeprefix("carpeta:")
			self._actualizar_archivos()

	def _actualizar_archivos(self) -> None:
		"""Filtra, ordena y vuelve a dibujar los archivos que coinciden."""
		if not hasattr(self, "tabla_archivos"):
			return

		consulta = self.busqueda.get().casefold().strip()
		carpeta_actual = self.carpeta_seleccionada
		# Al elegir una carpeta también se muestran sus subcarpetas.
		coincidentes = [
			archivo
			for archivo in self.archivos
			if (
				carpeta_actual == "."
				or archivo.carpeta.replace("\\", "/").strip("/") == carpeta_actual
				or archivo.carpeta.replace("\\", "/").strip("/").startswith(carpeta_actual + "/")
			)
			and (
				not consulta
				or consulta in archivo.nombre.casefold()
				or consulta in archivo.carpeta.casefold()
			)
		]

		ordenes = {
			"nombre": lambda archivo: archivo.nombre.casefold(),
			"carpeta": lambda archivo: archivo.carpeta.casefold(),
			"tamano": lambda archivo: archivo.tamano_bytes,
		}
		# Cada columna usa su propio criterio; el segundo clic invierte el orden.
		coincidentes.sort(key=ordenes[self.columna_orden], reverse=self.orden_inverso)
		archivos_existentes = self.tabla_archivos.get_children()
		if archivos_existentes:
			self.tabla_archivos.delete(*archivos_existentes)
		for indice, archivo in enumerate(coincidentes):
			self.tabla_archivos.insert(
				"",
				"end",
				iid=str(indice),
				values=(archivo.nombre, archivo.carpeta, formato_tamano(archivo.tamano_bytes)),
			)

		self.etiqueta_estado.configure(
			text=f"{len(coincidentes):,} archivos mostrados"
			+ (f" · {self.ruta_listado}" if self.ruta_listado else "")
		)

	def _ordenar(self, columna: str) -> None:
		"""Cambia la columna de orden o alterna la dirección de la actual."""
		if self.columna_orden == columna:
			self.orden_inverso = not self.orden_inverso
		else:
			self.columna_orden = columna
			self.orden_inverso = False
		self._actualizar_archivos()

	def _actualizar_resumen(self) -> None:
		"""Muestra el nombre del listado, el número de elementos y el tamaño total."""
		if not self.ruta_listado:
			return
		carpetas = {archivo.carpeta for archivo in self.archivos}
		tamano_total = sum(archivo.tamano_bytes for archivo in self.archivos)
		self.etiqueta_resumen.configure(
			text=(
				f"{self.ruta_listado.name}  ·  {len(self.archivos):,} archivos  ·  "
				f"{len(carpetas):,} carpetas  ·  {formato_tamano(tamano_total)} en total"
			)
		)


def main() -> None:
	"""Crea la ventana principal e inicia el bucle de eventos de Tkinter."""
	raiz = tk.Tk()
	VisorArchivos(raiz)
	raiz.mainloop()


if __name__ == "__main__":
	main()