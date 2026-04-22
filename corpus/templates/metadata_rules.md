
# Reglas de Metadata del Corpus

## knowledge_domain permitidos
- bian
- building_blocks
- guidelines_patterns

## source_type permitidos
- markdown_curated
- plain_text
- html_page

## status permitidos
- draft
- validated
- approved

## Campos obligatorios
- title
- knowledge_domain
- source_type
- document_name
- summary
- tags
- status
- last_reviewed

## Reglas generales
- Todo archivo debe iniciar con front matter YAML.
- El título debe ser claro y único.
- El summary debe tener entre 1 y 3 líneas.
- Las tags deben ser útiles para retrieval.
- Evitar copiar texto innecesario de fuentes.
- Priorizar contenido resumido y estructurado.
- No incluir información sensible.
- Enfocarse en arquitectura conceptual, no en código.