# Guía de Integración del Backend

Este documento explica cómo conectar el frontend del chatbot de la Policía Municipal con tu backend.

## Configuración Rápida

1. Abre el archivo `src/app/App.tsx`
2. Busca la sección `CONFIGURACIÓN DEL BACKEND`
3. Modifica la constante `API_URL` con la URL de tu API:

```typescript
const API_URL = 'https://tu-dominio.com/api/chat';
```

## Formato de la API

### Endpoint Requerido

**POST** `/api/chat` (o la ruta que prefieras)

### Petición (Request)

```json
{
  "message": "¿Cuál es el horario de atención?"
}
```

### Respuesta (Response)

```json
{
  "response": "La Jefatura de Policía atiende 24/7..."
}
```

## Ejemplo de Backend con Node.js + Express

```javascript
const express = require('express');
const cors = require('cors');
const app = express();

app.use(cors());
app.use(express.json());

app.post('/api/chat', (req, res) => {
  const { message } = req.body;
  
  // Aquí va tu lógica de IA/chatbot
  const botResponse = procesarMensaje(message);
  
  res.json({
    response: botResponse
  });
});

app.listen(3000, () => {
  console.log('Backend corriendo en puerto 3000');
});
```

## Ejemplo de Backend con Python + Flask

```python
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json()
    message = data.get('message', '')
    
    # Aquí va tu lógica de IA/chatbot
    bot_response = procesar_mensaje(message)
    
    return jsonify({
        'response': bot_response
    })

if __name__ == '__main__':
    app.run(port=3000)
```

## Consideraciones Importantes

### CORS (Cross-Origin Resource Sharing)

Si tu backend está en un dominio diferente al frontend, necesitas habilitar CORS:

**Node.js:**
```bash
npm install cors
```

**Python Flask:**
```bash
pip install flask-cors
```

### Variables de Entorno

Para diferentes ambientes (desarrollo, producción), puedes usar variables de entorno:

```typescript
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:3000/api/chat';
```

Crea un archivo `.env`:
```
VITE_API_URL=https://tu-api-produccion.com/api/chat
```

### Manejo de Errores

El frontend ya maneja:
- ✅ Errores de conexión
- ✅ Timeouts
- ✅ Respuestas inválidas
- ✅ Indicador de "escribiendo..." mientras espera respuesta

### Estructura de Mensajes

Cada mensaje tiene esta estructura:

```typescript
interface Message {
  id: string;           // ID único
  text: string;         // Contenido del mensaje
  sender: 'bot' | 'user'; // Quién envió el mensaje
  timestamp: Date;      // Fecha y hora
}
```

## Funcionalidades del Frontend

- ✅ Interfaz responsive (móvil y desktop)
- ✅ Historial de conversación
- ✅ Botón para reiniciar chat
- ✅ Indicador visual cuando el bot está escribiendo
- ✅ Scroll automático a nuevos mensajes
- ✅ Enter para enviar mensaje
- ✅ Deshabilitación del input durante envío
- ✅ Timestamps en cada mensaje
- ✅ Diferenciación visual entre bot y usuario

## Tecnologías de IA Recomendadas para el Backend

- **OpenAI GPT-4/GPT-3.5**: Para respuestas inteligentes
- **Anthropic Claude**: Alternativa a GPT
- **Dialogflow**: Para intenciones y entidades
- **Rasa**: Framework open source para chatbots
- **LangChain**: Para crear cadenas de procesamiento con LLMs

## Próximos Pasos

1. Implementa tu backend con la tecnología de tu elección
2. Configura la URL del API en `src/app/App.tsx`
3. (Opcional) Ajusta el formato de request/response según tu API
4. Habilita CORS en tu backend
5. ¡Prueba el chatbot!

## Soporte

Si tu API tiene un formato de respuesta diferente, modifica la función `getBotResponse` en `src/app/App.tsx` para adaptarla a tu estructura de datos.
