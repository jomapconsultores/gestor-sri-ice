import xml.etree.ElementTree as ET
from datetime import datetime

class AnnexGenerator:
    
    @staticmethod
    def componer_codigo_ice(factura):
        """Genera el codigo compuesto para el anexo ICE"""
        cod_impuesto = "3031"
        cod_clasificacion = "057"
        cod_marca = "000001"
        presentacion = "013"
        capacidad = "000750"
        unidad = "66"
        cod_pais = "593"
        grado = "000015"
        
        return f"{cod_impuesto}-{cod_clasificacion}-{cod_marca}-{presentacion}-{capacidad}-{unidad}-{cod_pais}-{grado}"
    
    @staticmethod
    def obtener_letra_tipo_id(tipo_id):
        """Convierte codigo de tipo ID a letra SRI"""
        mapeo = {'04': 'R', '05': 'C', '06': 'P', '07': 'F'}
        return mapeo.get(str(tipo_id).strip(), 'F')
    
    @staticmethod
    def generar_anexo(tipo, ruc, razon_social, anio, mes, facturas):
        """Genera el XML del anexo ICE o PVP"""
        
        root = ET.Element(tipo.lower())
        
        # Cabecera
        ET.SubElement(root, 'TipoIDInformante').text = 'R'
        ET.SubElement(root, 'IdInformante').text = ruc
        ET.SubElement(root, 'razonSocial').text = razon_social
        ET.SubElement(root, 'Anio').text = anio
        ET.SubElement(root, 'Mes').text = mes
        ET.SubElement(root, 'actImport').text = '02'
        ET.SubElement(root, 'codigoOperativo').text = tipo
        
        if tipo == 'PVP':
            ET.SubElement(root, 'tipoCarga').text = '1'
        
        # Ventas
        ventas = ET.SubElement(root, 'ventas')
        
        for factura in facturas:
            vta = ET.SubElement(ventas, 'vta')
            
            if tipo == 'ICE':
                codigo = AnnexGenerator.componer_codigo_ice(factura)
                letra_id = AnnexGenerator.obtener_letra_tipo_id(factura.ruc_comprador or '07')
                
                ET.SubElement(vta, 'codProdICE').text = codigo
                ET.SubElement(vta, 'gramoAzucar').text = '0.00'
                ET.SubElement(vta, 'tipoIdCliente').text = letra_id
                ET.SubElement(vta, 'idCliente').text = factura.ruc_comprador or '9999999999999'
                ET.SubElement(vta, 'tipoVentaICE').text = '1'
                ET.SubElement(vta, 'ventaICE').text = str(int(float(factura.base_ice or 0)))
                ET.SubElement(vta, 'devICE').text = '0'
                ET.SubElement(vta, 'cantProdBajaICE').text = '0'
            else:
                ET.SubElement(vta, 'codProdPVP').text = '3031'
                ET.SubElement(vta, 'gramoAzucar').text = '0.00'
                ET.SubElement(vta, 'precioExPVP').text = f"{float(factura.importe_total or 0):.2f}"
                ET.SubElement(vta, 'precioPVP').text = f"{float(factura.importe_total or 0) * 1.15:.2f}"
                ET.SubElement(vta, 'fechaInPVP').text = factura.fecha_emision.strftime('%d/%m/%Y') if factura.fecha_emision else ''
                ET.SubElement(vta, 'fechaFinPVP').text = ''
                ET.SubElement(vta, 'codPais').text = '593'
        
        xml_str = ET.tostring(root, encoding='UTF-8', xml_declaration=True)
        return xml_str