import ChatInterface from './features/ChatInterface'

function App() {
  return (
    <div className="flex h-screen w-screen bg-gray-50">
      <main className="mx-auto flex h-full w-full max-w-3xl flex-col">
        <header className="border-b border-gray-200 bg-white px-4 py-3">
          <h1 className="text-lg font-semibold text-gray-900">ChatbotAI</h1>
        </header>
        <div className="min-h-0 flex-1">
          <ChatInterface />
        </div>
      </main>
    </div>
  )
}

export default App
