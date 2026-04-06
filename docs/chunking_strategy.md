# Objetivo de la estrategia

La estrategia de chunking del MVP define cómo fragmentar el conocimiento antes de indexarlo en Azure AI Search para mejorar la recuperación de información, mantener calidad de respuesta y preservar trazabilidad hacia el documento fuente. En este proyecto, el chunking permite que el retrieval trabaje sobre unidades de contenido manejables, reduce ruido al responder preguntas específicas y facilita relacionar cada resultado con su origen, su dominio funcional y su posición dentro del documento padre.

Para el MVP, el conocimiento seguirá almacenándose en un solo índice físico con segmentación lógica mediante `knowledge_domain`, usando los dominios `bian`, `building_blocks` y `guidelines_patterns`. La estrategia aquí definida también deja preparada la base para el pipeline futuro de ingesta, embeddings e indexación sin introducir complejidad adicional fuera de la arquitectura ya acordada.

# Parámetros de chunking

La estrategia de chunking para el MVP será `recursive chunking`.

Los parámetros iniciales serán:

- `chunk size`: `1000`
- `overlap`: `200`

El uso de `recursive chunking` es adecuado para el MVP porque permite fragmentar documentos largos de forma controlada, intentando respetar estructuras naturales del texto antes de cortar arbitrariamente. Esto mejora la coherencia de cada fragmento y reduce la probabilidad de perder contexto importante dentro de una misma unidad indexada.

El valor de `chunk size = 1000` ofrece un equilibrio razonable entre contexto y precisión. Es suficientemente grande para conservar definiciones, explicaciones y relaciones útiles dentro de un mismo chunk, pero lo bastante acotado para evitar que un único fragmento mezcle demasiados temas y degrade el retrieval.

El valor de `overlap = 200` ayuda a preservar continuidad semántica entre chunks consecutivos. Para el MVP, este solapamiento reduce el riesgo de cortar conceptos relevantes en los límites del fragmento, especialmente en contenidos de arquitectura, definiciones de servicio y lineamientos donde una misma idea puede extenderse entre párrafos contiguos.

# Reglas para generación de chunks

Cada documento fuente puede generar múltiples chunks durante el proceso de ingestión.

Cada chunk debe conservar texto en lenguaje natural y representar un fragmento legible del contenido original. El objetivo no es transformar el conocimiento en una estructura nueva, sino dividirlo en unidades de recuperación útiles para búsqueda textual y vectorial.

El campo `content` debe contener el texto original del documento, o el fragmento correspondiente, sin resumir, reinterpretar ni transformar el contenido. Esto asegura fidelidad a la fuente, mejora la recuperación semántica y garantiza trazabilidad en las respuestas generadas por el sistema.

Los chunks no reemplazan el contenido original; lo fragmentan para facilitar indexación, retrieval y trazabilidad operativa. El documento padre sigue siendo la fuente primaria de referencia.

El texto principal de cada chunk se almacenará en el campo `content` del índice de Azure AI Search.

# Convención de chunk_order

El campo `chunk_order` representará la posición secuencial del chunk dentro del documento padre.

La numeración de `chunk_order` iniciará en `1`.

Cada chunk generado a partir de un mismo documento incrementará este valor de manera correlativa, por ejemplo `1`, `2`, `3`, `4`.

Esta convención permite reconstrucción lógica del documento, seguimiento del orden original del contenido y mejor trazabilidad durante reprocesamientos, validaciones de calidad y depuración del pipeline de ingesta.

# Convención de chunk_id

El campo `chunk_id` será un identificador lógico y estable del chunk.

Para el MVP se propone una convención simple basada en el documento padre y el número de chunk. Un formato recomendado es:

`{document_name}#chunk-{chunk_order}`

Ejemplo:

`customer-profile-service-domain-v10.pdf#chunk-1`

La estabilidad de `chunk_id` es importante para trazabilidad, reprocesamiento y comparación entre ejecuciones del pipeline cuando el contenido del documento no haya cambiado de forma material.

La diferencia entre `id` y `chunk_id` será la siguiente:

- `id` será el identificador único del registro indexado en Azure AI Search.
- `chunk_id` será el identificador lógico y estable del chunk para gobierno, trazabilidad y reprocesamiento.

En el MVP, `id` puede coincidir con `chunk_id` si se desea simplificar la implementación, pero conceptualmente ambos campos cumplen propósitos distintos y deben tratarse como separados en la especificación.

# Herencia de metadata del documento padre

Cada chunk debe heredar del documento padre, como mínimo, los siguientes campos:

- `title`
- `knowledge_domain`
- `source_type`
- `source_url`
- `document_name`
- `updated_at`
- metadata general útil para retrieval y trazabilidad

Esta herencia asegura que cada chunk conserve el contexto mínimo necesario para filtrar resultados, citar fuentes, reconstruir origen documental y aplicar controles básicos de gobierno del conocimiento.

En el MVP, el campo `metadata` se almacenará como texto JSON serializado. Esta decisión reduce complejidad operativa inicial y mantiene flexibilidad para incorporar atributos adicionales sin modificar de inmediato el esquema físico del índice.

# Convenciones de metadata operativa

Como propuesta mínima, cada chunk debería incluir en `metadata` atributos operativos como:

- `document_id`
- `document_version`
- `section`
- `uploaded_by`
- `source_system`
- `notes` si aplica

Esta metadata complementa los campos principales del índice y ayuda a mantener trazabilidad técnica y gobierno documental. No toda la metadata será usada directamente para búsqueda o ranking, pero sí será útil para auditoría, soporte operativo, validación de versiones, depuración y control del pipeline de ingesta.

Al almacenarse como JSON serializado en el MVP, estos atributos podrán evolucionar después sin bloquear la salida inicial del producto.

# Relación con retrieval

El campo `content` será usado para retrieval textual.

El campo `content_vector` será usado para retrieval vectorial.

El campo `knowledge_domain` se usará para filtros lógicos dentro del único índice físico del MVP, permitiendo acotar consultas a `bian`, `building_blocks` o `guidelines_patterns` según corresponda.

Los valores iniciales de retrieval para el MVP serán:

- `top-k = 5`
- `threshold de similitud = 0.78`

Estos valores son adecuados como punto de partida porque mantienen el conjunto recuperado en un tamaño manejable y favorecen resultados razonablemente cercanos al contexto consultado sin ampliar demasiado el ruido. De todos modos, ambos parámetros deberán considerarse configurables y podrán ajustarse posteriormente con pruebas de calidad de retrieval, revisión de respuestas y análisis de precisión.

# Ejemplo práctico

Supóngase un documento padre con estas características:

- `title`: `BIAN Customer Profile Service Domain Overview`
- `knowledge_domain`: `bian`
- `source_type`: `pdf`
- `source_url`: `https://example.org/bian/customer-profile`
- `document_name`: `customer-profile-service-domain-v10.pdf`
- `updated_at`: `2026-04-05T00:00:00Z`
- `metadata`: `{"document_id":"bian-customer-profile-v10","document_version":"10","section":"Customer Profile","uploaded_by":"architecture-team","source_system":"document_repository"}`

Ese documento podría generar chunks como los siguientes:

Chunk 1:

- `chunk_order`: `1`
- `chunk_id`: `customer-profile-service-domain-v10.pdf#chunk-1`
- `content`: `El dominio Customer Profile en BIAN permite gestionar la información del cliente y mantener una vista estructurada de sus datos relevantes para procesos de negocio y consulta operativa.`

Chunk 2:

- `chunk_order`: `2`
- `chunk_id`: `customer-profile-service-domain-v10.pdf#chunk-2`
- `content`: `Customer Profile mantiene atributos identificatorios, datos de segmentación y referencias necesarias para que otros dominios consulten información consistente del cliente dentro del entorno empresarial.`

Chunk 3:

- `chunk_order`: `3`
- `chunk_id`: `customer-profile-service-domain-v10.pdf#chunk-3`
- `content`: `Este Service Domain soporta actualización y consulta del perfil del cliente, y se relaciona con capacidades cercanas que consumen información confiable para originación, servicing y control operacional.`

En los tres casos, cada chunk hereda `title`, `knowledge_domain`, `source_type`, `source_url`, `document_name`, `updated_at` y la `metadata` operativa del documento padre. Esto permite que, al recuperar el chunk 2 por ejemplo, el sistema todavía pueda citar el documento completo, aplicar filtros por dominio `bian` y conservar el contexto mínimo para trazabilidad.

# Justificación para MVP

Esta estrategia es adecuada para el MVP por cuatro razones principales.

Primero, mantiene simplicidad. Un único índice físico en Azure AI Search con segmentación lógica por `knowledge_domain` reduce decisiones operativas y facilita una salida inicial controlada.

Segundo, introduce menor complejidad operativa. El uso de `recursive chunking`, metadata serializada y convenciones simples para `chunk_id` y `chunk_order` evita sobrecargar el pipeline temprano con reglas avanzadas que todavía no son necesarias.

Tercero, ofrece suficiente calidad inicial. Los parámetros definidos permiten recuperar fragmentos útiles, mantener continuidad entre chunks y sentar una base razonable para respuestas con fuentes en el caso de uso del copilot de gobernanza de arquitectura.

Cuarto, deja una buena base para escalar después. La estrategia es compatible con mejoras futuras en embeddings, ajustes de retrieval, enriquecimiento de metadata y evolución del proceso de ingestión sin romper el modelo lógico ya definido.

# Notas para implementación futura

Esta estrategia se conectará después con la Azure Function de procesamiento documental, que será responsable de leer documentos fuente, aplicar el `recursive chunking`, construir los chunks resultantes y preparar la metadata heredada y operativa por fragmento.

Sobre cada chunk se generarán embeddings para poblar `content_vector`, manteniendo `content` como base del retrieval textual y `knowledge_domain` como filtro lógico.

Posteriormente, cada chunk será indexado en Azure AI Search usando el esquema ya definido del proyecto: `id`, `chunk_id`, `chunk_order`, `content`, `title`, `knowledge_domain`, `source_type`, `source_url`, `document_name`, `metadata`, `updated_at` y `content_vector`.

En la capa de retrieval, el backend podrá consultar ese índice para recuperar hasta `5` resultados iniciales con un `threshold` de similitud de `0.78`, combinando luego esos resultados con trazabilidad de fuente para construir respuestas fundamentadas y con referencias al documento original.
