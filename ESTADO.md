# Estado del proyecto - Lead Magnet Auditoría

## Última sesión: 16 de mayo 2026

## Bloques completados
- ✅ Bloque 1: Formulario + endpoint base
- ✅ Bloque 2: Motor de análisis web + Instagram
- ✅ Bloque 2.5: Formulario inclusivo + publicidad cruzada
- ✅ Bloque 3: Generador de diagnóstico (migrado a DeepSeek)

## Stack actual
- FastAPI + Pydantic + Jinja2
- DeepSeek API (deepseek-chat) vía SDK openai
- Rotación multi-key con failover
- BeautifulSoup para análisis web
- python-dotenv para variables de entorno

## Sistema verificado end-to-end
- POST /auditar genera diagnóstico real
- JSON estructurado con: puntaje_general,
  resumen_ejecutivo, fortalezas, oportunidades,
  diagnostico_estrategico, servicios_sugeridos
- 21 tests pasando

## Pendientes prioritarios (para próxima sesión)

### 🔴 URGENTE - ajustar prompt en generador.py
Problema: cuando Instagram no se puede analizar
(perfil_existe: false por bloqueo de Instagram al
scraping desde servidor), el modelo dice
incorrectamente "tu perfil no existe".

Solución: ajustar PROMPT_SISTEMA y la construcción
del prompt de usuario para:
- Si datos_ig.perfil_existe es false → ignorar ese
  dato técnico
- Basarse SOLO en las 3 preguntas del usuario
  (frecuencia, estrategia, reto) para evaluar
  presencia social
- Nunca afirmar que "el perfil no existe" porque
  es una limitación técnica nuestra, no una realidad
- Asumir que SI el usuario completó las 3 preguntas
  es porque su Instagram SÍ existe

### 🟡 SEGURIDAD - rotar API key DeepSeek
La key actual pasó brevemente por .env.example
en un commit anterior. Por seguridad rotar en
https://platform.deepseek.com/api_keys

### 🔜 Próximos bloques
- Bloque 4: Generación de PDF con ReportLab
  (estilo dark Tuimagen, logo, navy + cyan,
  Space Grotesk)
- Bloque 5: Envío del PDF por email via Resend
  (remitente: naty@tuimagenstudios.com)
- Bloque 6: Guardar leads en base de datos
- Bloque 7: Deploy a Railway producción

## Variables de entorno (.env local)
- DEEPSEEK_MODEL=deepseek-chat
- DEEPSEEK_BASE_URL=https://api.deepseek.com
- DEEPSEEK_API_KEY_1=... (rotar)
- RESEND_API_KEY=re_... (configurada)

## Cómo retomar
1. cd al repo lead-magnet-auditoria
2. git pull origin main
3. .\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8010
4. Probar POST a /auditar para confirmar que
   sigue funcionando
