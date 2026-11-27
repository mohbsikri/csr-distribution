# [Solution Name] — Specification v2

**Source Artifact:** knowledge_base/extracted/[base]_knowledge_v[N].md  
**Source Type:** EXTRACTED  
**Generated:** [date]  
**Generation Command:** /generate-specification  
**Workspace:** [new_workspace_id]  
**Lineage:** [source_workspace_id] (v1 BASELINED [date])  
**ID Governance:** runtime/id_governance.md  
**Status:** DRAFT  

---

> **Guide de lecture v2**
>
> Ce document est le complément de la spécification v1 (BASELINED [date]). La frontière entre v1 et v2 est explicitement visible.
>
> - Règles **sans annotation** : héritées de v1, inchangées.
> - Règles annotées `[v2-added]` : nouvelles en v2.
> - Règles annotées `[v2-modified]` : existaient en v1, modifiées en v2.
> - Règles annotées `[DEPRECATED in v2]` : existaient en v1, supprimées ou remplacées en v2.
>
> La section **Δ v2** en fin de document récapitule toutes les modifications.

---

## 1. Terms and Definitions

[Terms inherited from v1 — unchanged]

[New v2 terms tagged `[v2-added]`:]

* **[Terme v2]** `[v2-added]` — Définition.

---

## 2. Context and Background

[Context inherited from v1. Modified sub-sections annotated.]

### System Identity

[Inherited — unchanged or annotated with `[v2-modified]` on modified lines.]

---

## 3. Design Decisions

[Design decisions inherited from v1 — unchanged.]

[New v2 decisions:]

* `[v2-added]` [Decision text.]

---

## 5. Constraints

**C-001** — [Inherited from v1.]

...

**C-008** — [Inherited from v1.]

**C-009** `[v2-added]`: [New constraint in v2.]

---

## 6. Business Rules

**BR-001** — [Inherited from v1, unchanged.]

...

**BR-015** — [Inherited from v1, unchanged.]

**BR-005** `[v2-modified]`: [Modified version of BR-005. Original v1 text preserved in the source workspace spec.]

**BR-013** `[DEPRECATED in v2]`: [Rule existed in v1 but is superseded in v2. ID not reused.]

**BR-016** `[v2-added]`: [New business rule introduced in v2.]

---

## 7. Technical Rules

**TR-001** — [Inherited from v1, unchanged.]

...

**TR-016** — [Inherited from v1, unchanged.]

**TR-017** `[v2-added]`: [New technical rule in v2.]

---

## Δ v2 — Modifications et Ajouts

> Cette section est le point d'entrée pour les testeurs et reviewers de v2. Elle liste uniquement les changements entre v1 et v2.

### Nouvelles règles (v2-added)

| ID | Type | Description courte |
|----|------|-------------------|
| BR-016 | Business Rule | [Description] |
| TR-017 | Technical Rule | [Description] |
| C-009 | Constraint | [Description] |

### Règles modifiées (v2-modified)

| ID | Type | Changement |
|----|------|-----------|
| BR-005 | Business Rule | [Nature du changement par rapport à v1] |

### Règles supprimées (DEPRECATED in v2)

| ID | Type | Raison |
|----|------|--------|
| BR-013 | Business Rule | [Raison de la suppression] |

### Résumé statistique

| Catégorie | v1 | v2-added | v2-modified | DEPRECATED | Total v2 actif |
|-----------|-----|----------|-------------|------------|----------------|
| BR | 15 | 1 | 1 | 1 | 15 |
| TR | 16 | 1 | 0 | 0 | 17 |
| C | 8 | 1 | 0 | 0 | 9 |
| **Total** | **39** | **3** | **1** | **1** | **41** |

*Total v2 actif = v1 + v2-added - DEPRECATED*

---

## Traceability Note

La traceability matrix v2 (`specifications/stable/[base]_traceability_v2.md`) couvre :
- Toutes les règles héritées de v1 (colonne `version_introduced: v1`)
- Toutes les règles nouvelles de v2 (colonne `version_introduced: v2`)
- Les règles modifiées (colonne `version_introduced: v1`, `version_updated: v2`)

Cette structure alimente directement la matrice de couverture de tests M-TC :
- **Suite régression** : toutes les règles `version_introduced: v1` non DEPRECATED
- **Suite nouvelles fonctionnalités** : toutes les règles `version_introduced: v2`
