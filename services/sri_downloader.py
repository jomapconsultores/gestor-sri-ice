import requests
import xml.etree.ElementTree as ET
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SRI_URLS = [
    "https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline",
    "https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline"
]


class SRIDownloader:
    
    @staticmethod
    def extraer_claves(texto):
        """Extrae claves de acceso de exactamente 49 digitos de un texto"""
        claves = re.findall(r'(?<!\d)\d{49}(?!\d)', texto)
        return list(set(claves))
    
    @staticmethod
    def descargar_xml(clave_acceso, output_folder):
        """Descarga un XML desde el SRI"""
        if not os.path.exists(output_folder):
            os.makedirs(output_folder, exist_ok=True)

        file_path = os.path.join(output_folder, f"{clave_acceso}.xml")

        if os.path.exists(file_path) and os.path.getsize(file_path) > 200:
            return file_path
        
        soap_body = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ec="http://ec.gob.sri.ws.autorizacion">
            <soapenv:Header/><soapenv:Body><ec:autorizacionComprobante><claveAccesoComprobante>{clave_acceso}</claveAccesoComprobante></ec:autorizacionComprobante></soapenv:Body></soapenv:Envelope>"""
        
        headers = {
            'Content-Type': 'text/xml; charset=utf-8',
            'User-Agent': 'Mozilla/5.0'
        }
        
        for url in SRI_URLS:
            try:
                response = requests.post(url, data=soap_body, headers=headers, timeout=15, verify=False)
                if response.status_code == 200:
                    root = ET.fromstring(response.content)
                    for node in root.iter():
                        if node.tag.endswith('comprobante') and node.text:
                            xml_str = node.text.replace("<![CDATA[", "").replace("]]>", "").strip()
                            if "<infoTributaria>" in xml_str:
                                with open(file_path, "w", encoding="utf-8") as f:
                                    f.write(xml_str)
                                return file_path
            except:
                pass
        
        return None
    
    @staticmethod
    def descargar_lote(claves, output_folder, progress_callback=None):
        """Descarga un lote de claves en paralelo"""
        resultados = {'descargados': [], 'errores': []}
        total = len(claves)
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futuros = {executor.submit(SRIDownloader.descargar_xml, c, output_folder): c for c in claves}
            
            for i, futuro in enumerate(as_completed(futuros)):
                clave = futuros[futuro]
                try:
                    ruta = futuro.result()
                    if ruta:
                        resultados['descargados'].append(ruta)
                    else:
                        resultados['errores'].append(clave)
                except:
                    resultados['errores'].append(clave)
                
                if progress_callback:
                    progress_callback(i + 1, total)
        
        return resultados