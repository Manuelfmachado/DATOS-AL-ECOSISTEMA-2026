ALBA Offline - Version descargable
====================================

QUE ES ALBA OFFLINE?
--------------------
ALBA Offline es la version 100% local de la plataforma de inteligencia
laboral ALBA. Funciona sin internet despues de la primera descarga de
modelos. Usa Gemma 4 E4B como motor de IA en lugar de Gemini cloud.

REQUISITOS DEL SISTEMA
----------------------
- Windows 10/11 (64-bit)
- Python 3.11+ (descarga: https://www.python.org/downloads/)
- 8 GB RAM minimo (16 GB recomendado)
- 10 GB espacio en disco
- GPU opcional (acelera la IA significativamente)

COMO USAR
---------
1. Descomprime este ZIP en una carpeta
2. Doble clic en iniciar_alba.bat
3. Se abre automaticamente una ventana de ALBA como una app nativa
4. Listo! Usa ALBA sin internet

NOTA: ALBA se abre como una ventana nativa (como VS Code),
sin navegador ni consola visible despues del inicio.

QUE INCLUYE
-----------
- Frontend: mismas 6 pantallas que ALBA Online
  * Observatorio Inteligente
  * Prediccion IA
  * Match Inteligente
  * Emprende IA
  * Coach IA (texto y voz)
  * Simulacion
  * Boton "Analizar con IA" en cada grafica

- Backend: FastAPI con todos los endpoints
- Base de datos: SQLite local con 44 tablas del DANE
- Modelos de IA (TODOS incluidos en el paquete, no se descarga nada):
  * Gemma 4 E4B IT (LLM + audio nativo) ~5 GB
  * Pocket TTS (TTS en espanol, voz "lola") ~450 MB
  * NO requiere internet en ningun momento

DIFERENCIAS CON ALBA ONLINE
---------------------------
| Aspecto          | Online              | Offline               |
|------------------|---------------------|-----------------------|
| Modelo IA        | Gemini 2.5 (nube)  | Gemma 4 E4B (local)   |
| Base de datos    | Supabase (nube)     | SQLite (local)        |
| Coach voz        | Gemini Live (nube)  | Gemma 4 E4B + Pocket TTS  |
| Internet         | Siempre requerido   | NUNCA (todo incluido)     |
| Velocidad        | Instantaneo         | Depende de tu PC      |

SOLUCION DE PROBLEMAS
---------------------
- "Python no encontrado": Instala Python 3.11+ y marca "Add to PATH"
- "Modelo no encontrado": Ejecuta descargar_modelos.py manualmente
- "Va lento": Si tienes GPU NVIDIA, el sistema la usa automaticamente
- "Error de memoria": Cierra otras aplicaciones, necesitas 8+ GB RAM
- "No abre el navegador": Abre manualmente http://localhost:8080

DETENER ALBA
------------
- Cierra la ventana de comandos (Ctrl+C)
- O cierra la terminal donde se esta ejecutando

CONTACTO
--------
Manuel Francisco Machado
Concurso Datos al Ecosistema 2026 - Reto 5: Economia y Empleo