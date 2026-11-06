#!/usr/bin/env python3
"""Cerebro Empresarial: CLI local operable por Codex. Sin llamadas de red ni instalaciones automáticas.

Uso: python scripts/cerebro.py --help
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

from doctor_preflight import diagnose

ROOT=Path(__file__).resolve().parent.parent


def parse_args():
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawTextHelpFormatter)
    sub=ap.add_subparsers(dest='comando',required=True)
    d=sub.add_parser('doctor',help='Diagnóstico de solo lectura: entorno y dependencias, no instala nada')
    d.add_argument('--vault',type=Path)
    c=sub.add_parser('crear',help='Crear una bóveda de empresa nueva desde plantilla, sin sobrescritura')
    c.add_argument('--id',required=True)
    c.add_argument('--nombre',required=True)
    c.add_argument('--dest',type=Path,required=True)
    e=sub.add_parser('estado',help='Mostrar resumen estructural de la empresa')
    e.add_argument('--vault',type=Path,required=True)
    f=sub.add_parser('ficha',help='Crear una ficha en borrador desde un tipo específico; sin inventar datos')
    f.add_argument('--vault',type=Path,required=True)
    f.add_argument('--tipo',required=True)
    f.add_argument('--titulo',required=True)
    f.add_argument('--resumen',default='')
    f.add_argument('--archivo',type=Path,help='Nota desarrollada en Markdown externo a Git/bóveda, sin YAML')
    f.add_argument('--fuente',action='append',default=[],help='ID de fuente ya registrada; se puede repetir')
    f.add_argument('--etiqueta',action='append',default=[],help='Etiqueta temática de Obsidian; repetible')
    s=sub.add_parser('fuente',help='Registrar referencia a una fuente, sin copiar documento original')
    s.add_argument('--vault',type=Path,required=True)
    s.add_argument('--id',required=True)
    s.add_argument('--titulo',required=True)
    s.add_argument('--localizador',required=True)
    s.add_argument('--clase',required=True)
    s.add_argument('--lectura',default='no_verificada',choices=['no_verificada','leida_parcial','leida_completa'])
    s.add_argument('--fecha-evento',default='')
    p=sub.add_parser('proponer',help='Registrar cambio sugerido en bandeja; NO toca la nota original')
    p.add_argument('--vault',type=Path,required=True)
    p.add_argument('--id',required=True,help='ID exacto de la nota objetivo')
    p.add_argument('--motivo',required=True)
    p.add_argument('--archivo',type=Path,required=True,help='Texto candidato en archivo local ya autorizado')
    arch=sub.add_parser('plan-conocimiento',help='Auditar mapa de notas, etiquetas y relaciones ANTES de redactar; solo lectura')
    arch.add_argument('--vault',type=Path,required=True)
    arch.add_argument('--archivo',type=Path,required=True,help='JSON estructurado preparado fuera de Git y de la bóveda')
    cap=sub.add_parser('capturar',help='Guardar hallazgos preliminares, sin declararlos conocimiento aprobado')
    cap.add_argument('--vault',type=Path,required=True)
    cap.add_argument('--titulo',required=True)
    cap.add_argument('--archivo',type=Path,required=True,help='Síntesis autorizada fuera de Git y la bóveda')
    cap.add_argument('--fuente',action='append',default=[],help='ID F-... ya registrado; repetible')
    doc=sub.add_parser('documento',help='Registrar un D01–D07/X01–X07 desarrollado sin aprobarlo')
    doc.add_argument('--vault',type=Path,required=True)
    doc.add_argument('--clase',required=True)
    doc.add_argument('--titulo',required=True)
    doc.add_argument('--archivo',type=Path,required=True,help='Markdown preparado fuera de la bóveda y Git')
    doc.add_argument('--doc-id',help='Identidad opcional Xnn-...; en Dnn coincide con clase')
    doc.add_argument('--estado',choices=['borrador','en_revision'],default='borrador')
    doc.add_argument('--cobertura',choices=['sin_fuente','parcial','suficiente_para_tarea','no_aplica'],
                     help='Cobertura declarada para la tarea; por defecto parcial con fuentes, sin_fuente sin ellas')
    doc.add_argument('--fecha-corte',help='YYYY-MM-DD; por defecto fecha de creación')
    doc.add_argument('--fuente',action='append',default=[],help='ID de fuente ya registrada; repetible')
    doc.add_argument('--etiqueta',action='append',default=[],help='Etiqueta temática de Obsidian; repetible')
    dprev=sub.add_parser('previsualizar-dx',help='Simular una modificación D/X sin escribir')
    dprev.add_argument('--vault',type=Path,required=True)
    dprev.add_argument('--doc-id',required=True)
    dprev.add_argument('--archivo',type=Path,required=True)
    dprev.add_argument('--fuente',action='append',default=[],help='ID de fuente correctiva ya registrada; repetible')
    dprep=sub.add_parser('preparar-dx',help='Guardar propuesta D/X sin modificar el documento actual')
    dprep.add_argument('--vault',type=Path,required=True)
    dprep.add_argument('--doc-id',required=True)
    dprep.add_argument('--archivo',type=Path,required=True)
    dprep.add_argument('--fuente',action='append',default=[],help='ID de fuente correctiva ya registrada; repetible')
    dapply=sub.add_parser('aplicar-dx',help='Aplicar propuesta D/X tras autorización específica y respaldo')
    dapply.add_argument('--vault',type=Path,required=True)
    dapply.add_argument('--propuesta',required=True)
    dapply.add_argument('--sha-original',required=True)
    dapply.add_argument('--sha-candidato',required=True)
    dapply.add_argument('--sha-fuentes',help='SHA-256 del conjunto de fuentes resultante cuando se añaden fuentes')
    dapply.add_argument('--responsable',required=True)
    dapply.add_argument('--referencia-autorizacion',required=True)
    dapply.add_argument('--respaldo',type=Path,required=True)
    drevert=sub.add_parser('restaurar-dx',help='Restaurar una versión D/X como revisión nueva tras autorización')
    drevert.add_argument('--vault',type=Path,required=True)
    drevert.add_argument('--doc-id',required=True)
    drevert.add_argument('--historial',required=True)
    drevert.add_argument('--sha-actual',required=True)
    drevert.add_argument('--responsable',required=True)
    drevert.add_argument('--referencia-autorizacion',required=True)
    drevert.add_argument('--respaldo',type=Path,required=True)
    rev=sub.add_parser('evaluar-dx',help='Registrar evaluación editorial de G1–G7 sin modificar D/X')
    rev.add_argument('--vault',type=Path,required=True)
    rev.add_argument('--doc-id',required=True)
    rev.add_argument('--acta',type=Path,required=True,help='JSON de revisión preparado fuera de Git y la bóveda')
    rev.add_argument('--sha-actual',required=True)
    approve=sub.add_parser('aprobar-dx',help='Promoción editorial integral con evaluación, autorización y respaldo')
    approve.add_argument('--vault',type=Path,required=True)
    approve.add_argument('--evaluacion',required=True)
    approve.add_argument('--sha-actual',required=True)
    approve.add_argument('--responsable',required=True)
    approve.add_argument('--referencia-autorizacion',required=True)
    approve.add_argument('--respaldo',type=Path,required=True)
    approve.add_argument('--confirmacion',required=True,help='APROBAR <doc_id> <12 primeros chars SHA>')
    rp=sub.add_parser('relacion-proponer',help='Crear propuesta de arista tipada, nunca aprobarla')
    rp.add_argument('--vault',type=Path,required=True)
    rp.add_argument('--origen',required=True)
    rp.add_argument('--destino',required=True)
    rp.add_argument('--predicado',required=True)
    rp.add_argument('--fuente',action='append',required=True)
    rp.add_argument('--ambito',required=True)
    rp.add_argument('--motivo',required=True)
    rq=sub.add_parser('relaciones',help='Consultar relaciones tipadas y su estado real')
    rq.add_argument('--vault',type=Path,required=True)
    rq.add_argument('--id',help='Filtrar por ID de origen o destino')
    rv=sub.add_parser('relacion-confirmar',help='Registrar ratificación humana de relación')
    rv.add_argument('--vault',type=Path,required=True)
    rv.add_argument('--relacion-id',required=True)
    rv.add_argument('--sha-relacion',required=True)
    rv.add_argument('--revisor',required=True)
    rv.add_argument('--referencia-autorizacion',required=True)
    rv.add_argument('--confirmacion',required=True)
    pilot=sub.add_parser('aceptacion',help='Preflight del piloto: lectura estructural, no aprobación humana')
    pilot.add_argument('--vault',type=Path,required=True)
    context=sub.add_parser('consulta-contextual',help='Candidatos de bloques por texto literal, fuente/fecha/autoridad')
    context.add_argument('--vault',type=Path,required=True)
    context.add_argument('--texto',required=True)
    context.add_argument('--tema')
    context.add_argument('--ambito')
    context.add_argument('--fecha')
    context.add_argument('--limite',type=int,default=10)
    context.add_argument('--orientar',action='store_true',help='Ordenar candidatos por términos de una petición natural; no genera respuesta semántica')
    k=sub.add_parser('continuidad',help='Registrar cierre de una sesión para recuperar contexto después')
    k.add_argument('--vault',type=Path,required=True)
    k.add_argument('--resumen',required=True)
    k.add_argument('--siguiente',required=True)
    k.add_argument('--revisado-por',default='por_validar')
    v=sub.add_parser('validar',help='Validar integridad de notas, ids, links y traspasos, NO verdad empresarial')
    v.add_argument('--vault',type=Path,required=True)
    q=sub.add_parser('buscar',help='Búsqueda textual con fuentes sin inferencias')
    q.add_argument('--vault',type=Path,required=True)
    q.add_argument('--texto',required=True)
    q.add_argument('--limite',type=int,default=12)
    a=sub.add_parser('autoridad',help='Consulta estricta por tema/ámbito/fecha declarada en contrato importado')
    a.add_argument('--vault',type=Path,required=True)
    a.add_argument('--tema',required=True)
    a.add_argument('--ambito',required=True)
    a.add_argument('--fecha',help='YYYY-MM-DD; si se omite, hoy')
    i=sub.add_parser('importar',help='Importar manifest vNext-0.9, no destructivo')
    i.add_argument('--vault',type=Path,required=True)
    i.add_argument('--manifest',type=Path,required=True)
    i.add_argument('--permitir-real',action='store_true',help='Con autorización: solo interno y previa revisión de fuentes')
    mapa=sub.add_parser('mapa-conocimiento',help='Previsualizar mapa Markdown/Canvas desde notas/relaciones sin escritura')
    mapa.add_argument('--vault',type=Path,required=True)
    mapa_apply=sub.add_parser('publicar-mapa',help='Publicar sólo mapa derivado, con SHA exacto y respaldo externo')
    mapa_apply.add_argument('--vault',type=Path,required=True)
    mapa_apply.add_argument('--sha-actual',required=True)
    mapa_apply.add_argument('--sha-propuesto',required=True)
    mapa_apply.add_argument('--confirmacion',required=True)
    mapa_apply.add_argument('--respaldo',type=Path,required=True)
    g=sub.add_parser('grafo',help='Exportar relaciones internas tipadas e hipervínculos')
    g.add_argument('--vault',type=Path,required=True)
    g.add_argument('--output',type=Path,help='Por defecto 90_Sistema/grafo.json')
    t=sub.add_parser('tipos',help='Mostrar tipos disponibles del modelo candidato y distinciones')
    t.add_argument('--tipo',help='Una clase concreta')
    return ap,ap.parse_args()


def run(args):
    cmd=args.comando
    if cmd=='doctor':return diagnose(args.vault)
    # Las dependencias solo se cargan DESPUÉS del diagnóstico. Útil para propietarios sin Python configurado.
    try:
        from crear_instancia import create
        from importar_traspaso import import_package
        from validar_boveda import validate
        from exportar_grafo import graph
        from operacion import (authority_lookup, create_ficha, create_source, exact_search,
                               load_registry, propose_change, save_continuity, summary)
    except ModuleNotFoundError as exc:
        hint = ('Antes de instalar, busca un Python o venv ya disponible con las dependencias '
                '(`command -v python3.11 python3.12 python3.13`; prueba `import yaml, jsonschema`) '
                'y repite ESTE comando con ese intérprete. ')
        if sys.platform == 'darwin':
            hint += 'En macOS comprueba también `/opt/homebrew/bin/python3.11`. '
        raise ValueError('Dependencia faltante en '+sys.executable+': '+str(exc)+'. '
                         +hint+'Sólo si ninguno funciona, solicita autorización para instalar requirements.txt en un venv.') from exc
    if cmd=='crear':return {'creada':str(create(args.id,args.nombre,args.dest)),'estado':'infraestructura_sin_conocimiento','nota':'Abrir y verificar manualmente en Obsidian'}
    if cmd=='estado':return summary(args.vault)
    if cmd=='ficha':return create_ficha(args.vault,args.tipo,args.titulo,resumen=args.resumen,sources=args.fuente,tags=args.etiqueta,content_file=args.archivo)
    if cmd=='fuente':return create_source(args.vault,args.id,args.titulo,args.localizador,args.clase,read_status=args.lectura,event_date=args.fecha_evento)
    if cmd=='proponer':
        f=args.archivo.expanduser().resolve()
        if not f.is_file() or f.stat().st_size>120000:
            raise ValueError('Archivo de propuesta inexistente o demasiado grande')
        return propose_change(args.vault,args.id,args.motivo,f.read_text(encoding='utf8'))
    if cmd=='plan-conocimiento':
        from plan_conocimiento import planificar
        return planificar(args.vault,args.archivo)
    if cmd=='capturar':
        from registro_descubrimiento import capture_discovery
        return capture_discovery(args.vault,args.titulo,args.archivo,sources=args.fuente)
    if cmd=='documento':
        from documentos import create_document
        return create_document(args.vault,args.clase,args.titulo,args.archivo,
                               doc_id=args.doc_id,sources=args.fuente,
                               editorial=args.estado,coverage=args.cobertura,
                               as_of=args.fecha_corte,tags=args.etiqueta)
    if cmd in {'previsualizar-dx','preparar-dx','aplicar-dx','restaurar-dx'}:
        from revisiones_dx import previsualizar, preparar, aplicar, restaurar
        if cmd=='previsualizar-dx':return previsualizar(args.vault,args.doc_id,args.archivo,sources=args.fuente)
        if cmd=='preparar-dx':return preparar(args.vault,args.doc_id,args.archivo,sources=args.fuente)
        if cmd=='aplicar-dx':return aplicar(args.vault,args.propuesta,expected_sha=args.sha_original,
                                           candidate_sha=args.sha_candidato,source_sha=args.sha_fuentes,
                                           responsable=args.responsable,
                                           referencia_autorizacion=args.referencia_autorizacion,
                                           backup_dir=args.respaldo)
        return restaurar(args.vault,args.doc_id,args.historial,expected_sha=args.sha_actual,
                        responsable=args.responsable,referencia_autorizacion=args.referencia_autorizacion,
                        backup_dir=args.respaldo)
    if cmd in {'evaluar-dx','aprobar-dx'}:
        from revision_editorial import registrar_evaluacion, aprobar_documento
        if cmd=='evaluar-dx':
            return registrar_evaluacion(args.vault,args.doc_id,args.acta,
                                        expected_sha=args.sha_actual)
        return aprobar_documento(args.vault,args.evaluacion,expected_sha=args.sha_actual,
                                responsable=args.responsable,
                                referencia_autorizacion=args.referencia_autorizacion,
                                backup_dir=args.respaldo,confirmacion=args.confirmacion)
    if cmd in {'relacion-proponer','relaciones','relacion-confirmar'}:
        from relaciones import propose,query,confirm
        if cmd=='relacion-proponer':
            return propose(args.vault,args.origen,args.destino,args.predicado,
                           fuentes=args.fuente,ambito=args.ambito,motivo=args.motivo)
        if cmd=='relaciones':
            return query(args.vault,source_id=args.id)
        return confirm(args.vault,args.relacion_id,args.sha_relacion,revisor=args.revisor,
                       referencia_autorizacion=args.referencia_autorizacion,
                       confirmacion=args.confirmacion)
    if cmd=='aceptacion':
        from aceptacion_piloto import preflight
        return preflight(args.vault)
    if cmd=='consulta-contextual':
        from consulta_contextual import consulta
        return consulta(args.vault,args.texto,tema=args.tema,ambito=args.ambito,
                        fecha=args.fecha,max_results=args.limite,orientar=args.orientar)
    if cmd=='continuidad':return save_continuity(args.vault,summary=args.resumen,next_step=args.siguiente,reviewer=args.revisado_por)
    if cmd=='validar':return validate(args.vault)
    if cmd=='buscar':return exact_search(args.vault,args.texto,args.limite)
    if cmd=='autoridad':return authority_lookup(args.vault,args.tema,args.ambito,as_of=args.fecha)
    if cmd=='importar':return import_package(args.manifest,args.vault,args.permitir_real)
    if cmd in {'mapa-conocimiento','publicar-mapa'}:
        from mapa_conocimiento import previsualizar as preview_map, publicar as publish_map
        if cmd=='mapa-conocimiento':
            return preview_map(args.vault)
        return publish_map(args.vault,sha_actual=args.sha_actual,
                           sha_propuesto=args.sha_propuesto,
                           confirmacion=args.confirmacion,backup_dir=args.respaldo)
    if cmd=='grafo':
        vault=args.vault.expanduser().resolve()
        out=(args.output or vault/'90_Sistema'/'grafo.json').expanduser().absolute()
        if vault not in out.parents:
            raise ValueError('El grafo debe guardarse dentro de la propia bóveda')
        data=graph(vault)
        out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8', newline='\n')
        return {'salida':str(out),'nodos':len(data['nodos']),'aristas':len(data['aristas'])}
    if cmd=='tipos':
        types=load_registry()
        if args.tipo:
            if args.tipo not in types:raise ValueError('Tipo desconocido: '+args.tipo)
            return types[args.tipo]
        return {'tipos':[{'tipo':t,'definicion':v['representa']} for t,v in types.items()],
                'aviso':'Propuesta operativa sujeta a pilotos; no taxonomía final'}
    raise ValueError('Comando no reconocido')


if __name__=='__main__':
    ap,args=parse_args()
    try:
        result=run(args)
        print(json.dumps(result,ensure_ascii=False,indent=2,default=str))
        if args.comando=='validar' and result.get('errores'):
            raise SystemExit(1)
    except (ValueError,FileExistsError,PermissionError,UnicodeError,KeyError,OSError) as e:
        print('ERROR:',str(e),file=sys.stderr)
        raise SystemExit(2)
