export default function MessageBubble({ role, content }) {
  const isUser = role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[75%] whitespace-pre-wrap rounded-lg px-4 py-2 text-sm leading-relaxed ${
          isUser
            ? 'rounded-br-sm bg-blue-600 text-white'
            : 'rounded-bl-sm bg-gray-100 text-gray-900'
        }`}
      >
        {content}
      </div>
    </div>
  )
}
