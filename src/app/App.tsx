import { useState, useRef, useEffect } from 'react';
import { Send, RotateCcw, Star } from 'lucide-react';

interface Message {
  id: string;
  text: string;
  sender: 'bot' | 'user';
  timestamp: Date;
}

// ====================================
// CONFIGURACIÓN DEL BACKEND
// ====================================
// Reemplaza esta URL con la URL de tu API backend
const API_URL = 'http://localhost:3000/api/chat'; // Ejemplo: 'https://tu-api.com/chat'

/**
 * Función para enviar mensaje al backend y obtener respuesta
 *
 * @param userMessage - El mensaje del usuario
 * @returns Promise con la respuesta del bot
 *
 * FORMATO ESPERADO DE LA PETICIÓN:
 * POST /api/chat
 * Body: { "message": "texto del usuario" }
 *
 * FORMATO ESPERADO DE LA RESPUESTA:
 * { "response": "texto de respuesta del bot" }
 */
async function getBotResponse(userMessage: string): Promise<string> {
  try {
    // Realiza la petición POST a tu backend
    const response = await fetch(API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message: userMessage }),
    });

    if (!response.ok) {
      throw new Error('Error en la respuesta del servidor');
    }

    const data = await response.json();

    // Ajusta según la estructura de respuesta de tu API
    return data.response || data.message || 'Lo siento, no pude procesar tu mensaje.';

  } catch (error) {
    console.error('Error al comunicarse con el backend:', error);
    return 'Lo siento, hay un problema de conexión. Por favor intenta más tarde.';
  }
}

// ====================================
// RESPUESTAS DE FALLBACK (OPCIONAL)
// ====================================
// Puedes eliminar esta sección si tu backend maneja todas las respuestas
// O mantenerla como fallback en caso de que el backend no esté disponible

export default function App() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      text: '¡Bienvenido al asistente virtual de la Jefatura de Policía Preventiva y Tránsito Municipal de Hermosillo! ¿En qué puedo ayudarte hoy?',
      sender: 'bot',
      timestamp: new Date()
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async () => {
    if (inputValue.trim() === '') return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text: inputValue,
      sender: 'user',
      timestamp: new Date()
    };

    const messageText = inputValue; // Guardar el mensaje antes de limpiar el input
    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsTyping(true);

    try {
      // Llamada al backend para obtener la respuesta
      const botResponseText = await getBotResponse(messageText);

      const botResponse: Message = {
        id: (Date.now() + 1).toString(),
        text: botResponseText,
        sender: 'bot',
        timestamp: new Date()
      };

      setMessages(prev => [...prev, botResponse]);
    } catch (error) {
      console.error('Error al obtener respuesta:', error);

      // Mensaje de error si falla la comunicación
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: 'Lo siento, ocurrió un error al procesar tu mensaje. Por favor intenta de nuevo.',
        sender: 'bot',
        timestamp: new Date()
      };

      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleResetChat = async () => {
    try {
      // Llamar al endpoint de reset del backend
      await fetch('http://localhost:3000/api/reset', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      // Limpiar mensajes localmente y mostrar mensaje de bienvenida
      setMessages([
        {
          id: '1',
          text: '¡Bienvenido al asistente virtual de la Jefatura de Policía Preventiva y Tránsito Municipal de Hermosillo! ¿En qué puedo ayudarte hoy?',
          sender: 'bot',
          timestamp: new Date()
        }
      ]);
      setInputValue('');
    } catch (error) {
      console.error('Error al reiniciar la conversación:', error);
      // Aún limpiar los mensajes localmente aunque falle el backend
      setMessages([
        {
          id: '1',
          text: '¡Bienvenido al asistente virtual de la Jefatura de Policía Preventiva y Tránsito Municipal de Hermosillo! ¿En qué puedo ayudarte hoy?',
          sender: 'bot',
          timestamp: new Date()
        }
      ]);
      setInputValue('');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="size-full flex flex-col bg-gradient-to-br from-slate-50 via-blue-50 to-slate-100">
      {/* Header */}
      <div className="bg-gradient-to-r from-[#2d3e7a] to-[#3d5099] shadow-lg">
        <div className="max-w-4xl mx-auto px-4 py-4 sm:py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="bg-white/95 p-2 sm:p-3 rounded-full shadow-md">
                <Star className="w-6 h-6 sm:w-8 sm:h-8 text-[#2d3e7a]" />
              </div>
              <div>
                <h1 className="text-white">GPH-Bot</h1>
                <p className="text-blue-200 text-sm sm:text-base">Hermosillo, Sonora</p>
              </div>
            </div>
            <button
              onClick={handleResetChat}
              className="flex items-center gap-2 bg-white/95 hover:bg-white text-[#2d3e7a] px-3 py-2 sm:px-4 sm:py-2 rounded-lg transition-all shadow-md hover:shadow-lg"
              aria-label="Reiniciar conversación"
            >
              <RotateCcw className="w-4 h-4 sm:w-5 sm:h-5" />
              <span className="hidden sm:inline">Reiniciar</span>
            </button>
          </div>
        </div>
      </div>

      {/* Chat Container */}
      <div className="flex-1 overflow-hidden">
        <div className="max-w-4xl mx-auto h-full flex flex-col">
          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] sm:max-w-[70%] rounded-2xl px-4 py-3 shadow-sm ${
                    message.sender === 'user'
                      ? 'bg-white text-gray-800 rounded-br-none border border-gray-200'
                      : 'bg-gradient-to-br from-[#3d5099] to-[#2d3e7a] text-white rounded-bl-none'
                  }`}
                >
                  <div className="flex items-start gap-2">
                    {message.sender === 'bot' && (
                      <Star className="w-5 h-5 flex-shrink-0 mt-0.5" />
                    )}
                    <div className="flex-1">
                      <p className="whitespace-pre-wrap break-words">{message.text}</p>
                      <p className="text-xs opacity-70 mt-1">
                        {message.timestamp.toLocaleTimeString('es-MX', {
                          hour: '2-digit',
                          minute: '2-digit'
                        })}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            ))}

            {isTyping && (
              <div className="flex justify-start">
                <div className="max-w-[80%] sm:max-w-[70%] rounded-2xl rounded-bl-none px-4 py-3 bg-gradient-to-br from-[#3d5099] to-[#2d3e7a] shadow-sm">
                  <div className="flex items-center gap-2">
                    <Star className="w-5 h-5 text-white" />
                    <div className="flex gap-1">
                      <div className="w-2 h-2 bg-white/80 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                      <div className="w-2 h-2 bg-white/80 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                      <div className="w-2 h-2 bg-white/80 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                    </div>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="p-4 bg-white border-t border-gray-200">
            <div className="max-w-4xl mx-auto">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Escribe tu pregunta aquí..."
                  className="flex-1 px-4 py-3 rounded-xl bg-gray-50 text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[#3d5099] focus:bg-white border border-gray-200 transition-all"
                  disabled={isTyping}
                />
                <button
                  onClick={handleSendMessage}
                  disabled={isTyping || inputValue.trim() === ''}
                  className="bg-gradient-to-r from-[#3d5099] to-[#2d3e7a] hover:from-[#4d60a9] hover:to-[#3d4e8a] disabled:from-gray-300 disabled:to-gray-400 disabled:cursor-not-allowed text-white p-3 rounded-xl transition-all shadow-sm hover:shadow-md flex items-center justify-center"
                  aria-label="Enviar mensaje"
                >
                  <Send className="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
