import zipfile
import os
import xml.etree.ElementTree as ET

docx = 'correciones.docx'
ext = 'correciones_ext'
os.makedirs(ext, exist_ok=True)
zipfile.ZipFile(docx, 'r').extractall(ext)
tree = ET.parse(ext + '/word/document.xml')
root = tree.getroot()
text = '\n'.join(p_text for p_text in (''.join(node.text for node in paragraph.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t') if node.text) for paragraph in root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p')) if p_text)
with open('correciones_texto.txt', 'w', encoding='utf-8') as f:
    f.write(text)
print("Done")
