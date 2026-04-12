# Componente de procesamiento documental

## Objetivo del componente

El componente de procesamiento documental del MVP de "Architecture Governance Copilot" tiene como propósito transformar documentos de texto plano en unidades de conocimiento listas para una etapa posterior de ingestión. Su responsabilidad actual es leer un archivo `.txt`, normalizar su contenido, fragmentarlo en chunks coherentes y construir una salida estructurada con metadata operativa básica.

En esta fase MVP, el componente no realiza indexación, generación de embeddings ni persistencia externa. Su alcance se concentra en preparar datos consistentes y reutilizables para las siguientes etapas del pipeline.

## Arquitectura del procesamiento

La implementación se organiza en dos piezas complementarias:

### Módulo reusable

El módulo principal se encuentra en `src/processing/document_processor.py`. Aquí reside la lógica de negocio del procesamiento documental, desacoplada de la capa de ejecución. Esta decisión permite reutilizar la misma lógica desde ejecución local, pruebas o integraciones futuras sin depender directamente de Azure Functions.

El módulo concentra tres responsabilidades centrales:

- limpieza del texto de entrada
- chunking recursivo con overlap
- construcción de registros de salida con metadata

### Azure Function wrapper

El wrapper se encuentra en `apps/document_processor_function/function_app.py`. Su función es exponer el procesamiento como un endpoint HTTP y delegar el trabajo real al módulo reusable.

Esta capa se encarga de:

- recibir la solicitud HTTP
- validar que el cuerpo sea JSON válido
- exigir los campos `file_path`, `knowledge_domain` y `source_type`
- invocar `process_document`
- devolver una respuesta JSON con el resultado o con errores de validación

Con este diseño, Azure Function actúa como punto de entrada del componente, mientras que la lógica de transformación permanece encapsulada en un módulo independiente.

## Flujo de procesamiento

El procesamiento sigue una secuencia simple y explícita:

### Lectura

El módulo recibe la ruta del archivo a procesar mediante `file_path`. En el estado actual del MVP, solo se aceptan archivos con extensión `.txt`. Si el archivo no existe o no cumple con el tipo soportado, el proceso devuelve un error de validación.

### Limpieza

Antes de fragmentar el contenido, el texto pasa por una rutina de limpieza básica. Esta etapa normaliza saltos de línea, elimina caracteres no deseados, corrige espacios redundantes y reduce bloques excesivos de líneas vacías.

La limpieza no resume, interpreta ni altera el significado del documento. Su objetivo es dejar el contenido en una forma estable para el chunking.

### Chunking

Una vez limpio el texto, el módulo aplica chunking recursivo. La fragmentación intenta respetar primero separaciones naturales del contenido, priorizando párrafos y luego oraciones. Solo cuando eso no es suficiente, el corte se realiza por límites de caracteres.

Después de obtener fragmentos base, el proceso compone chunks finales mediante una ventana deslizante con solapamiento entre bloques consecutivos. Esto permite mantener continuidad semántica entre chunks cercanos.

### Metadata

Por cada chunk generado, el sistema construye un registro estructurado con campos de identificación, trazabilidad y contexto documental. Además de los campos principales, se agrega una metadata operativa serializada en JSON para mantener flexibilidad en el MVP sin complejizar todavía el esquema físico de almacenamiento.

## Estrategia de chunking aplicada

La estrategia usada en el MVP es `recursive chunking`, alineada con la definición previa del proyecto.

Los parámetros configurados actualmente son:

- `chunk_size`: `1000`
- `overlap`: `200`

La lógica recursiva sigue este orden:

1. dividir por párrafos cuando existen separaciones naturales
2. dividir por oraciones cuando el párrafo todavía excede el tamaño objetivo
3. dividir por caracteres cuando no es posible preservar una estructura textual mayor

Esta estrategia es adecuada para el MVP porque mantiene un equilibrio razonable entre coherencia del contenido, continuidad contextual y simplicidad de implementación.

## Estructura de salida

El resultado del procesamiento es una lista de registros, uno por cada chunk generado. Cada registro contiene información orientada a ingestión posterior y trazabilidad del documento origen.

La salida incluye los siguientes atributos:

- `id`: identificador único generado para el registro
- `chunk_id`: identificador lógico del chunk con el formato `{document_name}#chunk-{chunk_order}`
- `chunk_order`: posición secuencial del chunk dentro del documento
- `content`: texto del chunk
- `title`: nombre del documento
- `knowledge_domain`: dominio de conocimiento recibido en la solicitud
- `source_type`: tipo de fuente recibido en la solicitud
- `source_url`: actualmente `null`
- `document_name`: nombre del archivo procesado
- `metadata`: JSON serializado con metadata operativa básica
- `updated_at`: timestamp UTC del procesamiento

La metadata serializada incluye, en esta versión del MVP:

- `document_id`
- `document_version`
- `section`
- `uploaded_by`
- `source_system`

## Integración futura

El componente actual deja preparada la base para integraciones posteriores sin introducir todavía dependencias adicionales dentro del MVP.

### Embeddings

Cada chunk generado podrá alimentar una etapa posterior de generación de embeddings sobre el campo de contenido. Esto permitirá incorporar retrieval vectorial sin modificar la lógica base de limpieza y chunking ya implementada.

### Azure AI Search

La estructura de salida ya está alineada con el esquema lógico definido para el índice del proyecto. Esto facilita que una etapa posterior tome los registros generados y los envíe a Azure AI Search para indexación textual y, más adelante, híbrida.

### Blob Storage

Aunque el componente actual procesa archivos locales `.txt`, la separación entre wrapper y lógica reusable permite conectar en el futuro una fuente de documentos alojados en Blob Storage sin rehacer el núcleo del procesamiento.

## Notas para MVP

El componente actual responde a una necesidad concreta del MVP: validar el flujo de preparación documental antes de incorporar servicios adicionales. Su implementación prioriza simplicidad, trazabilidad y reutilización.

Las restricciones actuales del alcance son deliberadas:

- solo procesa archivos `.txt`
- no genera embeddings
- no indexa en Azure AI Search
- no persiste resultados en Blob Storage
- no incorpora enriquecimiento documental adicional

Con estas decisiones, el proyecto mantiene una base técnica clara para evolucionar después hacia un pipeline completo de ingestión documental sin sobrediseñar la primera versión.
