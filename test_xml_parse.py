"""Script de prueba para verificar que parse_xml_gasto_completo funciona"""
import sys
sys.path.insert(0, '.')

from services.gastos_processor import parse_xml_gasto_completo

# Test: Buscar un XML de ejemplo
import os
import glob

# Buscar XMLs en el proyecto
xml_files = glob.glob('./sri_downloads/**/*.xml', recursive=True)[:3]

if xml_files:
    print(f"✓ Encontrados {len(xml_files)} XMLs para prueba")
    for xml_path in xml_files:
        print(f"\n📄 Probando: {xml_path}")
        datos = parse_xml_gasto_completo(xml_path)
        
        if datos:
            print(f"  ✓ Parseado exitosamente")
            print(f"    RUC Emisor: {datos['ruc_emisor']}")
            print(f"    Nombre: {datos['nombre_emisor']}")
            print(f"    Fecha: {datos['fecha']}")
            print(f"    Total: ${datos['total']}")
            print(f"    Base 15%: ${datos['base_15']} | IVA: ${datos['iva_15']}")
            print(f"    Concepto: {datos['concepto']}")
        else:
            print(f"  ✗ Error al parsear")
else:
    print("⚠ No se encontraron XMLs para prueba. Descargue algunos primero.")
