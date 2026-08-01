"""
XML Metadata Parser (Module 5)
"""
import xml.etree.ElementTree as ET

def parse_info_xml(xml_path: str):
    tree = ET.parse(xml_path)
    return tree.getroot()
