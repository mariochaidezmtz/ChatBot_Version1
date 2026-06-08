import { useState, useRef, useEffect } from 'react';
import bgImage from '../imports/image-2.png';
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
  const [isOpen, setIsOpen] = useState(false);
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

  const handleResetChat = () => {
    setMessages([
      {
        id: '1',
        text: '¡Bienvenido al asistente virtual de la Jefatura de Policía Preventiva y Tránsito Municipal de Hermosillo! ¿En qué puedo ayudarte hoy?',
        sender: 'bot',
        timestamp: new Date()
      }
    ]);
    setInputValue('');
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="size-full relative"
      style={{
        backgroundImage: `url(${bgImage})`,
        backgroundSize: 'cover',
        backgroundPosition: 'top left',
        backgroundRepeat: 'no-repeat',
      }}
    >
      {/* Floating Toggle Button */}
      <div className="fixed bottom-6 right-6 z-50">
        {!isOpen && (
          <>
            <span className="absolute inset-0 rounded-full bg-[#3d5099] opacity-40 animate-ping" />
            <span className="absolute inset-0 rounded-full bg-[#3d5099] opacity-20 animate-ping" style={{ animationDelay: '0.4s' }} />
          </>
        )}
        <button
          onClick={() => setIsOpen(prev => !prev)}
          className="relative w-16 h-16 rounded-full bg-gradient-to-br from-[#3d5099] to-[#2d3e7a] shadow-2xl hover:shadow-blue-400/40 hover:scale-110 active:scale-95 transition-all flex items-center justify-center"
          aria-label={isOpen ? 'Cerrar asistente' : 'Abrir asistente de Policía Municipal'}
        >
          <span className="transition-transform duration-300" style={{ transform: isOpen ? 'rotate(90deg)' : 'rotate(0deg)' }}>
            {isOpen ? (
              <svg xmlns="http://www.w3.org/2000/svg" className="w-7 h-7 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            ) : (
              <Star className="w-8 h-8 text-white fill-white" />
            )}
          </span>
        </button>
      </div>

      {/* Chat Widget */}
      {isOpen && (
        <div
          className="fixed bottom-24 right-6 z-40 w-[360px] sm:w-[400px] max-h-[600px] flex flex-col rounded-2xl shadow-2xl overflow-hidden border border-blue-100"
          style={{ animation: 'chatSlideIn 0.3s cubic-bezier(0.34,1.56,0.64,1) both', boxShadow: '0 8px 40px rgba(45,62,122,0.25)' }}
        >
          {/* Header */}
          <div className="bg-gradient-to-r from-[#2d3e7a] to-[#3d5099] px-4 py-3 flex items-center justify-between flex-shrink-0">
            <div className="flex items-center gap-2">
              <div className="bg-white/20 p-1.5 rounded-full">
                <Star className="w-5 h-5 text-white fill-white" />
              </div>
              <div>
                <p className="text-white text-sm">GPH-Bot</p>
                <p className="text-blue-200 text-xs">Hermosillo, Sonora</p>
              </div>
            </div>
            <button
              onClick={handleResetChat}
              className="flex items-center gap-1 bg-white/15 hover:bg-white/25 text-white px-2.5 py-1.5 rounded-lg transition-all text-xs"
              aria-label="Reiniciar conversación"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Reiniciar</span>
            </button>
          </div>

          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto px-3 py-4 space-y-3 bg-gradient-to-br from-slate-50 via-blue-50 to-slate-100" style={{ maxHeight: '420px' }}>
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[85%] rounded-2xl px-3 py-2.5 shadow-sm text-sm ${
                    message.sender === 'user'
                      ? 'bg-white text-gray-800 rounded-br-none border border-gray-200'
                      : 'bg-gradient-to-br from-[#3d5099] to-[#2d3e7a] text-white rounded-bl-none'
                  }`}
                >
                  <div className="flex items-start gap-2">
                    {message.sender === 'bot' && (
                      <Star className="w-4 h-4 flex-shrink-0 mt-0.5 fill-white" />
                    )}
                    <div className="flex-1">
                      <p className="whitespace-pre-wrap break-words">{message.text}</p>
                      <p className="text-xs opacity-60 mt-1">
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
                <div className="rounded-2xl rounded-bl-none px-3 py-2.5 bg-gradient-to-br from-[#3d5099] to-[#2d3e7a] shadow-sm">
                  <div className="flex items-center gap-2">
                    <Star className="w-4 h-4 text-white fill-white" />
                    <div className="flex gap-1">
                      <div className="w-1.5 h-1.5 bg-white/80 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                      <div className="w-1.5 h-1.5 bg-white/80 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                      <div className="w-1.5 h-1.5 bg-white/80 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                    </div>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="p-3 bg-white border-t border-gray-200 flex-shrink-0">
            <div className="flex gap-2">
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Escribe tu pregunta aquí..."
                className="flex-1 px-3 py-2.5 rounded-xl bg-gray-50 text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[#3d5099] focus:bg-white border border-gray-200 transition-all text-sm"
                disabled={isTyping}
              />
              <button
                onClick={handleSendMessage}
                disabled={isTyping || inputValue.trim() === ''}
                className="bg-gradient-to-r from-[#3d5099] to-[#2d3e7a] hover:from-[#4d60a9] hover:to-[#3d4e8a] disabled:from-gray-300 disabled:to-gray-400 disabled:cursor-not-allowed text-white p-2.5 rounded-xl transition-all shadow-sm hover:shadow-md flex items-center justify-center"
                aria-label="Enviar mensaje"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
