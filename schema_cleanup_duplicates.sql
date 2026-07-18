-- ============================================================================
-- Limpieza de duplicados en Supabase
-- Conserva solo la fila con MAX(id) por clave natural (carga más reciente).
-- Ejecutar en: Supabase Studio → SQL Editor → Run
-- ============================================================================

BEGIN;

-- ole_ingresos_por_nivel: 49 reales, 98 cargados (x2)
DELETE FROM public.ole_ingresos_por_nivel
WHERE id NOT IN (
  SELECT MAX(id) FROM public.ole_ingresos_por_nivel
  GROUP BY nivel_formacion, rango_ingreso
);

-- ole_ingresos_por_programa: ~37k reales, 74k cargados (x2)
DELETE FROM public.ole_ingresos_por_programa
WHERE id NOT IN (
  SELECT MAX(id) FROM public.ole_ingresos_por_programa
  GROUP BY programa, rango_ingreso, graduados, porcentaje
);

-- saberpro_resumen_programas: 458 reales, 2340 cargados (x5)
DELETE FROM public.saberpro_resumen_programas
WHERE id NOT IN (
  SELECT MAX(id) FROM public.saberpro_resumen_programas
  GROUP BY institucion, programa, departamento
);

-- ole_ingresos_por_ies: verificar duplicados (552 filas)
DELETE FROM public.ole_ingresos_por_ies
WHERE id NOT IN (
  SELECT MAX(id) FROM public.ole_ingresos_por_ies
  GROUP BY ies
);

-- geih_empleo_depto_sector: duplicados por (dpto, rama_ciiu, periodo)
DELETE FROM public.geih_empleo_depto_sector
WHERE id NOT IN (
  SELECT MAX(id) FROM public.geih_empleo_depto_sector
  GROUP BY dpto, rama_ciiu, periodo
);

-- snies_programas_matriculados: duplicados por (institucion, programa, departamento, nucleo_conocimiento)
DELETE FROM public.snies_programas_matriculados
WHERE id NOT IN (
  SELECT MAX(id) FROM public.snies_programas_matriculados
  GROUP BY institucion, programa, departamento, nucleo_conocimiento
);

-- Normalizar nombres de departamentos con mojibake (opcional, recomendado)
-- Descomenta y ejecuta si quieres limpiar BOGOTÁ, CHOCÓ, etc.
-- UPDATE public.geih_resumen_departamento
-- SET departamento = translate(
--     regexp_replace(departamento, '[^a-zA-Z0-9 .]', '', 'g'),
--     'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
--     'abcdefghijklmnopqrstuvwxyz'
-- );

COMMIT;

-- Verificación post-limpieza (correr aparte):
-- SELECT 'ole_nivel' AS t, COUNT(*) FROM ole_ingresos_por_nivel
-- UNION ALL SELECT 'ole_prog', COUNT(*) FROM ole_ingresos_por_programa
-- UNION ALL SELECT 'saberpro', COUNT(*) FROM saberpro_resumen_programas
-- UNION ALL SELECT 'ole_ies', COUNT(*) FROM ole_ingresos_por_ies;
-- Resultado esperado: 49, ~37000, 458, 552
