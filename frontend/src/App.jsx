import React, { useState } from 'react'
import Sidebar from './components/Sidebar'
import Header from './components/Header'
import ProjectInspector from './components/ProjectInspector'
import Stage3Placeholder from './components/Stage3Placeholder'
import ChatInterface from './features/ChatInterface'
import ErrorBoundary from './components/ErrorBoundary'
import { useConversations } from './features/useConversations'

export default function App() {
  const {
    conversationList,
    activeConversationId,
    messages,
    isLoading,
    isHistoryLoading,
    error,
    handleNewChat,
    handleSelectConversation,
    handleSendMessage,
  } = useConversations()

  const [currentView, setCurrentView] = useState('chat') // 'chat' | 'project'
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const [isInspectorOpen, setIsInspectorOpen] = useState(false)

  const safeConversationList = Array.isArray(conversationList) ? conversationList.filter(Boolean) : []
  const activeConversation = safeConversationList.find(
    (c) => c && c.id === activeConversationId
  ) || null

  return (
    <ErrorBoundary>
      <div className="flex h-screen w-screen overflow-hidden bg-[#141313] text-[#ededed] font-mono antialiased">
        {/* Sidebar navigation */}
        <Sidebar
          conversationList={safeConversationList}
          activeConversationId={activeConversationId}
          onSelectConversation={handleSelectConversation}
          onNewChat={handleNewChat}
          isOpen={isSidebarOpen}
          onClose={() => setIsSidebarOpen(false)}
        />

        {/* Main Workspace */}
        <div className="flex min-w-0 flex-1 flex-col overflow-hidden bg-[#141313]">
          <Header
            activeConversation={activeConversation}
            currentView={currentView}
            onViewChange={setCurrentView}
            onOpenSidebar={() => setIsSidebarOpen(true)}
            isInspectorOpen={isInspectorOpen}
            onToggleInspector={() => setIsInspectorOpen((prev) => !prev)}
          />

          {/* Content & Inspector Flex Container */}
          <div className="flex min-h-0 flex-1 overflow-hidden">
            {/* Main Content Pane */}
            <main className="min-h-0 flex-1 overflow-hidden bg-[#141313]">
              {currentView === 'chat' ? (
                <ChatInterface
                  messages={messages}
                  isLoading={isLoading}
                  isHistoryLoading={isHistoryLoading}
                  error={error}
                  onSendMessage={handleSendMessage}
                  activeConversationId={activeConversationId}
                />
              ) : (
                <Stage3Placeholder />
              )}
            </main>

            {/* Right Project Inspector Panel */}
            <ProjectInspector
              isOpen={isInspectorOpen}
              onClose={() => setIsInspectorOpen(false)}
            />
          </div>
        </div>
      </div>
    </ErrorBoundary>
  )
}
