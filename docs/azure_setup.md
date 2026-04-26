# Objetivo de la configuración Azure

La configuración base de Azure para el MVP de "Architecture Governance Copilot" define una estructura mínima y clara de recursos para soportar el desarrollo, la integración y las pruebas iniciales del proyecto. Esta base permite organizar los componentes según su propósito, facilitar la administración compartida del equipo y reducir complejidad operativa en una fase temprana.

Para el MVP, la prioridad es contar con una estructura simple, suficiente para desplegar la solución y habilitar el trabajo coordinado entre los integrantes, sin introducir capas adicionales de infraestructura que todavía no son necesarias.

# Estructura de Resource Groups

Para el MVP se usarán dos resource groups:

## `rg-agc-app-dev`

Este resource group tendrá como propósito alojar la capa de aplicación.

Aquí se ubicarán recursos asociados a:

- frontend
- servicios de aplicación
- posibles recursos de autenticación

## `rg-agc-data-dev`

Este resource group tendrá como propósito alojar la capa de datos e inteligencia.

Aquí se ubicarán recursos asociados a:

- Azure Blob Storage
- Azure AI Search
- Azure OpenAI
- Azure Function de procesamiento documental
- Azure Data Factory
- almacenamiento de contexto

La separación en dos resource groups permite distinguir de manera simple la capa de aplicación de la capa de datos e inteligencia, manteniendo una organización suficiente para el MVP sin añadir complejidad innecesaria.

# Naming Convention

La convención de nombres del proyecto usará el prefijo `agc`, correspondiente a `Architecture Governance Copilot`.

El formato general será:

`{tipo}-{proyecto}-{capa}-{entorno}`

Ejemplos:

- `rg-agc-app-dev`
- `rg-agc-data-dev`

Para el MVP, el entorno usado será únicamente `dev`. No se crearán entornos adicionales como `test` o `prod` en esta etapa.

# Permisos y control de acceso

La asignación base de permisos será la siguiente:

- Usuario principal: `Owner` heredado a nivel de suscripción
- Segundo integrante: `Contributor` en `rg-agc-app-dev` y `rg-agc-data-dev`

Ambos integrantes cuentan con permisos suficientes para desplegar y gestionar recursos en los resource groups definidos.

En esta fase:

- ambos pueden desplegar recursos
- no se restringe por componente en el MVP
- el control se realiza por acuerdo de equipo, no por IAM granular

Este enfoque prioriza velocidad de trabajo y simplicidad operativa, suficiente para una solución en fase inicial con un equipo pequeño y responsabilidades coordinadas.

# Distribución de responsabilidades

La distribución principal de componentes será la siguiente:

## Rony

Responsable principal de:

- Azure AI Search
- Azure OpenAI
- Azure Function
- backend e integración con IA

## José Luis

Responsable principal de:

- frontend
- Blob Storage
- Data Factory
- carga de documentos

Aunque existe esta distribución principal, ambos integrantes pueden apoyar transversalmente en cualquier componente cuando sea necesario para desbloquear trabajo, validar integraciones o ajustar configuraciones compartidas.

# Decisiones para MVP

Para el MVP se han definido las siguientes decisiones base:

- se usa un solo entorno: `dev`
- se evita separación `dev`/`prod`
- se prioriza simplicidad sobre complejidad
- se minimiza costo y esfuerzo operativo

Estas decisiones son consistentes con el alcance actual del proyecto, permiten avanzar con rapidez y reducen sobrecarga administrativa mientras se valida el flujo integral del copilot.

# Notas para siguientes tareas

Esta configuración servirá como base para las siguientes tareas del proyecto:

- `T22`: aprovisionamiento de Azure AI Search
- `T23`: Azure OpenAI
- `T26`: procesamiento documental
- despliegue del backend y frontend

La estructura propuesta permitirá ubicar cada recurso en su capa correspondiente, mantener claridad operativa y facilitar la evolución del MVP sin rehacer la organización inicial de Azure.
