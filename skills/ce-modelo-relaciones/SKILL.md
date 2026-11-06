---
name: ce-modelo-relaciones
description: "Differentiate entity types and build verifiable relations in Obsidian: offers, products, services, clients, meetings, processes, projects and sources."
---

# ce-modelo-relaciones

**0. Architecture first:** activate `ce-arquitectura-conocimiento`. Do not create a note per mention. Decide what has its own identity and lifecycle, what exists, what stays in the source and what is a link. Validate with the product's `plan-conocimiento` flow read-only (upstream [Obsidian-Bussines-Brain](https://github.com/unsulabs/Obsidian-Bussines-Brain); not bundled in this plugin); tags are for navigation, edges with source/scope for modeling relations — do not confuse the two.

1. Consult `modelo/tipos_entidad.json` ([upstream](https://github.com/unsulabs/Obsidian-Bussines-Brain/blob/main/modelo/tipos_entidad.json)), the D/X catalog and the vNext-0.9 handover contract ([upstream](https://github.com/unsulabs/Obsidian-Bussines-Brain/blob/main/metodologia/vNext-1.0R/Contrato_Traspaso_Obsidian_Agentes_vNext.md)). The registry is a candidate: justify separations by identity, changes, history, permissions, reuse and query.
2. Before creating, check whether the entity already exists by ID, authoritative system, alias and context. A mention does NOT force a note.
3. Verify distinctions: product/offer; consulting/tool; project/case/session/meeting; client-account/person/organization; offer/proposal/agreement; research/result.
4. If a unit needs its own file, create it as a draft with `brain_create_vault` (upstream: `python scripts/cerebro.py ficha --vault ... --tipo ... --titulo ...`). Link registered sources.
5. Register typed relations with evidence, directionality and scope; do not use generic `related` as authority. Avoid duplicating price, financial state or contract across several notes.
6. Run `brain_validate_vault` after changes and inspect the graph (Obsidian Graph view); the Graph view shows navigation, not truth. Test one real question and one negative.
**Output:** justified entities, explicit relations, sources, and presence/absence of ambiguous cases.
