# Fuentes de datos

ALBA utiliza exclusivamente **datos abiertos de [datos.gov.co](https://datos.gov.co)** y portales oficiales colombianos.

## Fuentes colombianas (datos.gov.co)

### DANE — Gran Encuesta Integrada de Hogares (GEIH)
- **URL:** https://microdatos.dane.gov.co/index.php/catalog/Mercado_Laboral
- **Entidad:** DANE
- **Qué da:** Empleo, desempleo, informalidad, salarios por ocupación y departamento
- **Periodo:** 2022-2026 (mensual)
- **Tablas en ALBA:** 9 tablas (~120K filas)
- **Uso:** Observatorio, Predicción, Match (salarios reales)

### DANE — EMICRON (Encuesta de Micronegocios)
- **URL:** https://microdatos.dane.gov.co/index.php/catalog/875
- **Entidad:** DANE
- **Qué da:** Micronegocios por sector, departamento, motivos de emprendimiento
- **Periodo:** 2020-2023
- **Tablas en ALBA:** 5 tablas (~109 filas)
- **Uso:** Emprende IA

### DNP — Medición del Desempeño Municipal (MDM)
- **URL:** https://www.datos.gov.co/Estadisticas-Nacionales/Medici-n-del-Desempe-o-Municipal-MDM/nkjx-rsq7
- **Entidad:** DNP
- **Qué da:** Índice de desempeño municipal por dimensiones
- **Tablas en ALBA:** 3 tablas (~22K filas)
- **Uso:** Observatorio (contexto territorial)

### MinTrabajo — PILA (Plan Integrado de Liquidación de Aportes)
- **URL:** https://www.datos.gov.co/Trabajo-y-Pensiones/Pensionados-y-Cotizantes-de-PILA-Boletin-Mensual-/8pqf-rmzr
- **Entidad:** MinTrabajo
- **Qué da:** Cotizantes formales por sector económico (CIIU)
- **Tablas en ALBA:** 2 tablas (~652 filas)
- **Uso:** Observatorio, Predicción

### Confecámaras — RUES (Registro Único de Empresas)
- **URL:** https://www.rues.org.co
- **Entidad:** Confecámaras
- **Qué da:** Empresas nuevas por sector CIIU y cámara de comercio
- **Tablas en ALBA:** 3 tablas (~26K filas)
- **Uso:** Observatorio (sectores emergentes), Emprende IA

### MEN — SNIES (Sistema Nacional de Información de Educación Superior)
- **URL:** https://www.datos.gov.co/Ciencia-Tecnologia-e-Innovacion/Sistema-Nacional-de-Informacion-de-la-Educacion-Su
- **Entidad:** MEN
- **Qué da:** Programas académicos matriculados por institución y departamento
- **Tablas en ALBA:** 2 tablas (~85K filas)
- **Uso:** Match (oferta educativa)

### MEN — OLE/ETDH (Observatorio Laboral para la Educación)
- **URL:** https://www.datos.gov.co/Ciencia-Tecnologia-e-Innovacion/Programas-de-Educaci-n-para-el-Trabajo-y-el-Desarr/2v94-3ypi
- **Entidad:** MEN
- **Qué da:** Ingresos reales de egresados por programa, área, nivel e institución
- **Tablas en ALBA:** 7 tablas (~37K filas)
- **Uso:** Match (salarios reales por carrera), Predicción

### SENA — Programas activos + SPE/APE
- **URL:** https://www.datos.gov.co/Trabajo-y-Pensiones/Servicio-Publico-de-Empleo-SPE-Apuntados-por-Ocupac/8pqf-rmzr
- **Entidad:** SENA
- **Qué da:** Cursos SENA activos + inscritos en Servicio Público de Empleo
- **Tablas en ALBA:** 4 tablas (~17K filas)
- **Uso:** Match (cursos complementarios), Predicción

### MEN — Saber Pro
- **URL:** https://www.datos.gov.co/Ciencia-Tecnologia-e-Innovacion
- **Entidad:** MEN
- **Qué da:** Resultados de pruebas Saber Pro por programa e institución
- **Tablas en ALBA:** 1 tabla (~1.4K filas)
- **Uso:** Match (calidad educativa)

## Fuentes internacionales

### ESCO (European Skills/Competences, Occupations)
- **URL:** https://esco.ec.europa.eu
- **Qué da:** Taxonomía de ocupaciones y habilidades (europaea, universal)
- **Tablas en ALBA:** 7 tablas (~155K filas)
- **Uso:** Match (habilidades por ocupación)

### O*NET (Occupational Information Network)
- **URL:** https://www.onetcenter.org
- **Qué da:** Ocupaciones estandarizadas con habilidades, tareas y herramientas
- **Versión:** 30.3
- **Tablas en ALBA:** 7 tablas (~12K filas)
- **Uso:** Match, Coach, Predicción

### World Bank Open Data
- **URL:** https://data.worldbank.org/country/colombia
- **API:** https://api.worldbank.org/v2/country/COL/indicator/{indicator}
- **Qué da:** Indicadores macroeconómicos de Colombia (2010-2025)
- **Tablas en ALBA:** 1 tabla (128 registros)
- **Uso:** Predicción (Chronos T5)

## Validación de uso de datos abiertos

Todos los datasets utilizados son:
- ✅ Públicos y de acceso libre
- ✅ De fuentes oficiales (gobiernos o entidades supranacionales)
- ✅ En formatos abiertos (CSV, JSON, API REST)
- ✅ Reutilizables sin restricciones
- ✅ **Disponibles en [datos.gov.co](https://datos.gov.co)** (excepto ESCO, O*NET y World Bank)

La mayoría están disponibles en **datos.gov.co** o en portales oficiales de las entidades colombianas (DANE, MEN, MinTrabajo, DNP, SENA, Confecámaras).