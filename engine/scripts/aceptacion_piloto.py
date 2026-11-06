"""Preflight de aceptación read-only para un piloto con Obsidian + Codex.

Las pruebas automatizadas NO equivalen a pruebas de interfaz, criterio experto,
recuperación semántica, respaldo real o autorización humana.
"""
from __future__ import annotations

from pathlib import Path
import json
import yaml

from operacion import safe_vault, summary
from validar_boveda import validate


def preflight(vault_path:Path) -> dict:
    vault,cfg=safe_vault(vault_path)
    integrity=validate(vault)
    state=summary(vault)
    view_folder=vault/"90_Sistema"/"Vistas"
    names=sorted(view_folder.glob("*.base"))
    view_checks=[]
    for path in names:
        try:
            obj=yaml.safe_load(path.read_text(encoding="utf8"))
            flt=obj.get("filters") if isinstance(obj,dict) else None
            terms=flt.get("and",[]) if isinstance(flt,dict) else []
            excluded=any(isinstance(term,dict)
                         and 'file.inFolder("90_Sistema/Plantillas")'
                         in (term.get("not") or []) for term in terms)
            has_format='file.ext == "md"' in terms
            valid=bool(isinstance(obj,dict) and obj.get("views")
                       and isinstance(terms,list)
                       and excluded and has_format)
        except (OSError,UnicodeError,yaml.YAMLError,ValueError):
            valid=False
        view_checks.append({"vista":path.name,"sin_plantillas":valid})
    views_ok=len(view_checks)==16 and all(x["sin_plantillas"] for x in view_checks)
    docs=state.get("documentos_dx",{})
    has_doc=docs.get("total",0)>0
    actual_errors=integrity.get("errores",[])
    structural_ok=not actual_errors
    stages={
        "integridad_y_referencias":"PASS" if structural_ok else "FAIL",
        "bases_sin_falsos_registros":"PASS" if views_ok else "PENDIENTE_MIGRACION_O_VALIDACION",
        "primera_unidad_empresarial":"REGISTRADA_NO_APROBADA" if has_doc else "PENDIENTE",
        "calidad_editorial_humana":"NO_VERIFICADO",
        "obsidian_gui_real":"NO_VERIFICADO",
        "obsidian_cli_real":"NO_VERIFICADO",
        "recuperacion_por_fuente_y_contexto":"NO_VERIFICADO",
        "permisos_reales_y_resguardo":"NO_VERIFICADO",
        "restauracion_en_copia_aislada":"NO_VERIFICADO",
        "segunda_sesion_con_codex":"NO_VERIFICADO",
    }
    return {
        "empresa_id":cfg["company_id"],"version_instancia":cfg.get("version_instancia"),
        "estado_tecnico":"APTO_PARA_PILOTO_LOCAL" if structural_ok and views_ok and has_doc else
                         "REQUIERE_ATENCION",
        "producto_listo_para_produccion":False,
        "documentos_dx":docs.get("total",0),
        "fuentes_registradas":state["capas"]["fuentes"],
        "capas":state["capas"],
        "continuidad_reciente":state.get("ultima_continuidad"),
        "continuidades_fecha_invalida":state.get("continuidades_fecha_invalida",[]),
        "vistas_bases":view_checks,
        "errores_estructurales":actual_errors,
        "gates":stages,
        "limite":"Este reporte no ejecuta Obsidian GUI, no valida semántica ni revisa permisos del SO",
    }
