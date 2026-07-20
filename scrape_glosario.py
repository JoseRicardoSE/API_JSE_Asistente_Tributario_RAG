import requests
from bs4 import BeautifulSoup
import os

def scrape_glosario():
    base_url = "https://www.sii.cl/ayudas/ayudas_por_servicios/4669-{}.html"
    letras = "abcdefghijklmnopqrstuvwxyz"
    
    # Algunas letras pueden no existir o tener la url principal (la A es 4669-.html)
    urls = [("a", "https://www.sii.cl/ayudas/ayudas_por_servicios/4669-.html")]
    for letra in letras[1:]:
        urls.append((letra, base_url.format(letra)))
        
    md_content = "# Glosario Tributario SII\n\n"
    md_content += "Los términos acá contenidos no reemplazan ni modifican las definiciones legales. Sirven como referencia técnica y ayuda.\n\n"
    
    print("Iniciando scraping del Glosario SII...")
    for letra, url in urls:
        print(f"Scrapeando letra {letra.upper()}...")
        try:
            response = requests.get(url, timeout=10)
            response.encoding = 'utf-8'
            if response.status_code != 200:
                print(f"  [!] Letra {letra.upper()} no disponible (HTTP {response.status_code})")
                continue
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # En el HTML del SII, los conceptos suelen estar en <strong> o <b> seguidos de texto.
            # Veamos la estructura real. Generalmente es una lista <dl> o párrafos con <strong>
            
            # El contenido principal está en un div con class="col-sm-9 contenido text-justify"
            contenido_div = soup.find('div', class_='contenido')
            if not contenido_div:
                continue
                
            md_content += f"## Letra {letra.upper()}\n\n"
            
            # Encontremos los términos
            # La mayoría de los glosarios del SII usan <p><strong>Termino:</strong> definicion</p>
            # Vamos a iterar sobre todos los <p>
            for p in contenido_div.find_all('p'):
                strong = p.find(['strong', 'b'])
                if strong and strong.text.strip():
                    term = strong.text.strip().rstrip(':.-')
                    
                    # Remover el strong del p para obtener solo la definición
                    strong.extract()
                    definicion = p.text.strip()
                    
                    if len(term) > 2 and len(definicion) > 5:
                        md_content += f"### {term}\n{definicion}\n\n"
                        
        except Exception as e:
            print(f"  [X] Error en letra {letra.upper()}: {e}")
            
    os.makedirs('documentos_legales_md', exist_ok=True)
    with open('documentos_legales_md/glosario_sii.md', 'w', encoding='utf-8') as f:
        f.write(md_content)
        
    print("Scraping finalizado. Guardado en documentos_legales_md/glosario_sii.md")

if __name__ == "__main__":
    scrape_glosario()
