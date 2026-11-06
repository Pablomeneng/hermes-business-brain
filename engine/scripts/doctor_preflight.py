"""Diagnóstico de cero dependencias. Debe funcionar incluso si PyYAML/jsonschema NO están instalados."""
from __future__ import annotations
from importlib import util
import json
import os
from pathlib import Path
import platform
import shutil
import sys


def diagnose(vault=None):
    cli=shutil.which('obsidian')
    candidates=[]
    if sys.platform=='darwin':
        candidates=[Path('/Applications/Obsidian.app'),Path.home()/'Applications'/'Obsidian.app']
    elif sys.platform=='win32':
        candidates=[Path(os.environ.get('LOCALAPPDATA',''))/'Programs/Obsidian/Obsidian.exe']
    else:
        candidates=[Path('/usr/bin/obsidian'),Path('/opt/Obsidian/obsidian')]
    modules={name:'LOCALIZADO' if util.find_spec(name) else 'NO INSTALADO' for name in ('yaml','jsonschema')}
    result={'producto':'Cerebro Empresarial 0.4.0-rc.1',
            'so':platform.platform(), 'python':sys.version.split()[0], 'recomendado_python':'3.11+',
            'directorio_trabajo':str(Path.cwd()),'dependencias_python':modules,
            'obsidian_ruta_cli':cli,'candidatos_obsidian':[str(p) for p in candidates if p.exists()],
            'obsidian_version':'NO VERIFICADO', 'obsidian_gui':'NO VERIFICADO',
            'bases':'NO VERIFICADO','templates':'NO VERIFICADO',
            'acceso_a_archivos_empresariales':'NO VERIFICADO',
            'instalacion_real':'NO HECHA POR ESTE COMANDO',
            'siguiente':'Pedir autorización de instalaciones y ruta antes de cualquier escritura'}
    if vault is not None:
        p=Path(vault).expanduser().resolve()
        result['boveda_solicitada']=str(p)
        result['config_empresa_existe']=(p/'90_Sistema/config_empresa.yaml').is_file()
        result['nota']='Existencia de config no demuestra integridad/identidad; ejecutar validar tras instalar dependencias'
    return result
