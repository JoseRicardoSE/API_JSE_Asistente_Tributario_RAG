import os
import glob

def clean_md_files():
    # Diccionario de reemplazos exactos (usando el caracter de reemplazo unicode \ufffd)
    replacements = {
        "Art\ufffdculo": "Artículo",
        "art\ufffdculo": "artículo",
        "T\ufffdtulo": "Título",
        "t\ufffdtulo": "título",
        "P\ufffdrrafo": "Párrafo",
        "p\ufffdrrafo": "párrafo",
        "N\ufffdmero": "Número",
        "n\ufffdmero": "número",
        "N\ufffd": "N°",
        "1\ufffd": "1°",
        "2\ufffd": "2°",
        "3\ufffd": "3°",
        "4\ufffd": "4°",
        "5\ufffd": "5°",
        "6\ufffd": "6°",
        "7\ufffd": "7°",
        "8\ufffd": "8°",
        "9\ufffd": "9°",
        "0\ufffd": "0°",
        "\ufffdltima": "Última",
        "Publicaci\ufffdn": "Publicación",
        "publicaci\ufffdn": "publicación",
        "Promulgaci\ufffdn": "Promulgación",
        "Versi\ufffdn": "Versión",
        "versi\ufffdn": "versión",
        "A\ufffdo": "Año",
        "a\ufffdo": "año",
        "Seg\ufffdn": "Según",
        "seg\ufffdn": "según",
        "M\ufffds": "Más",
        "m\ufffds": "más",
        "Tambi\ufffdn": "También",
        "tambi\ufffdn": "también",
        "As\ufffd": "Así",
        "as\ufffd": "así",
        "S\ufffdlo": "Sólo",
        "s\ufffdlo": "sólo",
        "Aplicaci\ufffdn": "Aplicación",
        "aplicaci\ufffdn": "aplicación",
        "Declaraci\ufffdn": "Declaración",
        "declaraci\ufffdn": "declaración",
        "Infracci\ufffdn": "Infracción",
        "infracci\ufffdn": "infracción",
        "Direcci\ufffdn": "Dirección",
        "direcci\ufffdn": "dirección",
        "Excepci\ufffdn": "Excepción",
        "excepci\ufffdn": "excepción",
        "Sanci\ufffdn": "Sanción",
        "sanci\ufffdn": "sanción",
        "Exenci\ufffdn": "Exención",
        "exenci\ufffdn": "exención",
        "Tributaci\ufffdn": "Tributación",
        "tributaci\ufffdn": "tributación",
        "Retenci\ufffdn": "Retención",
        "retenci\ufffdn": "retención",
        "Operaci\ufffdn": "Operación",
        "operaci\ufffdn": "operación",
        "obligaci\ufffdn": "obligación",
        "Obligaci\ufffdn": "Obligación",
        "Disposici\ufffdn": "Disposición",
        "disposici\ufffdn": "disposición",
        "Fracci\ufffdn": "Fracción",
        "fracci\ufffdn": "fracción",
        "resoluci\ufffdn": "resolución",
        "Resoluci\ufffdn": "Resolución",
        "informaci\ufffdn": "información",
        "Informaci\ufffdn": "Información",
        "Instituci\ufffdn": "Institución",
        "instituci\ufffdn": "institución",
        "Aprobaci\ufffdn": "Aprobación",
        "aprobaci\ufffdn": "aprobación",
        "Fijaci\ufffdn": "Fijación",
        "fijaci\ufffdn": "fijación",
        "reajustar\ufffdn": "reajustarán",
        "pagar\ufffdn": "pagarán",
        "deber\ufffdn": "deberán",
        "est\ufffdn": "están",
        "podr\ufffd": "podrá",
        "Podr\ufffd": "Podrá",
        "ser\ufffd": "será",
        "Ser\ufffd": "Será",
        "estar\ufffd": "estará",
        "Estar\ufffd": "Estará",
        "aplicar\ufffd": "aplicará",
        "Aplicar\ufffd": "Aplicará"
    }

    files = glob.glob('documentos_legales_md/*.md')
    print(f"Archivos encontrados: {len(files)}")
    
    for filepath in files:
        # No toquemos el glosario que creamos nosotros recién
        if "glosario_sii" in filepath:
            continue
            
        print(f"Procesando: {os.path.basename(filepath)}")
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            
        # Reemplazar usando el diccionario
        for bad_word, good_word in replacements.items():
            content = content.replace(bad_word, good_word)
            
        # Reemplazos finales para evitar que queden "\ufffd" huérfanos sin dañar la estructura
        # Si un \ufffd está suelto, lo eliminamos o convertimos a espacio
        # pero es mejor dejar los que no conocemos explícitamente para no fusionar palabras.
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
            
    print("¡Limpieza de Diccionario completada exitosamente!")

if __name__ == "__main__":
    clean_md_files()
