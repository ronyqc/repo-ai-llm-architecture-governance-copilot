# Esquema Lógico del Índice de Búsqueda

## Propósito del índice

El índice en Azure AI Search servirá como base de recuperación de conocimiento para el MVP de "Architecture Governance Copilot". Su función será almacenar contenido normalizado y segmentado para permitir búsquedas textuales, trazabilidad de fuentes y evolución posterior hacia recuperación híbrida con embeddings.

## Decisión de diseño

Para el MVP se usará:

- Un solo índice físico en Azure AI Search.
- Segmentación lógica mediante el campo `knowledge_domain`.

Esta decisión permite centralizar la administración del contenido sin perder la capacidad de filtrar información por dominio funcional.

## Tabla del esquema lógico del índice

| Campo | Tipo de dato | Obligatorio | Filtrable | Buscable | Descripción |
| --- | --- | --- | --- | --- | --- |
| `id` | `string` | Sí | Sí | No | Identificador único del registro indexado. |
| `content` | `string` | Sí | No | Sí | Texto principal del chunk o unidad de conocimiento. |
| `title` | `string` | Sí | Sí | Sí | Título descriptivo del contenido o documento origen. |
| `knowledge_domain` | `string` | Sí | Sí | No | Dominio lógico al que pertenece el contenido. |
| `source_type` | `string` | Sí | Sí | No | Tipo de fuente de origen, por ejemplo documento o guía. |
| `source_url` | `string` | No | Sí | No | URL o referencia de ubicación de la fuente original. |
| `document_name` | `string` | Sí | Sí | No | Nombre del documento de origen del contenido indexado. |
| `chunk_order` | `int` | No | Sí | No | Posición secuencial del chunk dentro del documento. |
| `metadata` | `string` | No | No | No | Metadatos serializados en texto JSON para simplificar el MVP y facilitar enriquecimiento posterior. |
| `updated_at` | `datetime` | Sí | Sí | No | Fecha y hora de última actualización del registro. |
| `content_vector` | `collection(float)` | No | No | No | Vector de embeddings asociado al contenido para retrieval vectorial futuro; su dimensión dependerá del modelo de embeddings configurado más adelante. |
| `chunk_id` | `string` | No | Sí | No | Identificador estable del chunk para trazabilidad y reprocesamiento. |

## Convenciones de uso por campo

- Los campos `title` y `content` serán los principales para búsqueda y retrieval textual.
- El campo `content_vector` se reservará para retrieval vectorial.
- Los campos `knowledge_domain` y `source_type` se usarán principalmente para filtros.
- Los campos `document_name`, `source_url`, `id` y `chunk_id` soportarán la trazabilidad de fuentes.

## Dominios de conocimiento

El campo `knowledge_domain` deberá aceptar únicamente estos valores:

- `bian`: contenido relacionado con marcos, conceptos y estructuras de BIAN.
- `building_blocks`: contenido asociado a bloques de arquitectura, capacidades reutilizables y componentes base ya publicados como catálogos.
- `guidelines_patterns`: contenido orientado a lineamientos, buenas prácticas y patrones de arquitectura relacionado a Building Blocks.

## Justificación para MVP

Para el MVP se recomienda un solo índice físico porque reduce complejidad operativa, simplifica la configuración inicial y evita fragmentar el modelo de recuperación en múltiples estructuras. También disminuye el costo de administración, facilita la mantenibilidad y permite validar rápidamente el flujo de indexación y consulta sin introducir una separación física que todavía no es necesaria. La segmentación lógica mediante `knowledge_domain` cubre la necesidad actual de aislar contextos de conocimiento sin perder flexibilidad de consulta.

## Notas para siguientes tareas

Este esquema se conecta directamente con las siguientes capacidades que se incorporarán después:

- `chunking`: el contenido podrá dividirse en fragmentos y registrarse mediante `chunk_id` y `chunk_order`.
- `embeddings`: el campo `content_vector` permitirá almacenar representaciones vectoriales.
- `Azure AI Search`: el índice podrá configurarse para búsqueda textual y, más adelante, búsqueda vectorial.
- `retrieval`: las consultas podrán combinar filtrado por `knowledge_domain` con recuperación de contenido relevante.
- `respuestas con fuentes`: los metadatos de trazabilidad permitirán devolver referencias claras al usuario final.
