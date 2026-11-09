# Listado de archivos

Este programa recorre un directorio y todos sus subdirectorios, y genera un
listado de los archivos encontrados en formato JSON. Para cada archivo incluye
su nombre y tamaño en bytes, agrupados por carpeta.

## Requisitos

- Python 3

## Uso

Ejecuta el programa indicando la ruta del directorio que quieres listar:

```powershell
python listado.py "C:\ruta\al\directorio"
```

Si no indicas una ruta, el programa te la pedirá:

```powershell
python listado.py
```

El programa guarda el resultado en `listado.json`, en el directorio desde el
que se ejecuta, y muestra la ruta del archivo generado.

## Visor gráfico

Para consultar un listado en una interfaz gráfica, ejecuta:

```powershell
python visor.py
```

El visor carga automáticamente `listado.json` si está junto a `visor.py`.
También puedes usar **Abrir listado…** para elegir otro archivo JSON. Permite
explorar las carpetas, buscar por nombre o carpeta y ordenar por nombre,
carpeta o tamaño. Utiliza Tkinter, incluido en las distribuciones habituales
de Python, por lo que no requiere instalar paquetes adicionales.

## Formato del resultado

El JSON agrupa los archivos por carpeta relativa al directorio analizado. Los
archivos que estén directamente en el directorio se agrupan bajo `"."`.

```json
{
  ".": [
    {
      "nombre": "documento.txt",
      "tamano_bytes": 128
    }
  ],
  "imagenes": [
    {
      "nombre": "foto.jpg",
      "tamano_bytes": 2048
    }
  ]
}
```

Si la ruta indicada no existe o no es un directorio válido, el programa informa
del error.
