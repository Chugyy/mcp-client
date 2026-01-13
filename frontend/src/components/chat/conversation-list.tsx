"use client"

import { useState } from 'react'
import Link from 'next/link'
import { Input } from '@/components/ui/input'
import {
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarMenuAction
} from '@/components/ui/sidebar'
import { Button } from '@/components/ui/button'
import { useChatContext } from '@/contexts/chat-context'
import { MessageSquare, Plus, Search, Trash2 } from 'lucide-react'

export function ConversationList() {
  const [searchQuery, setSearchQuery] = useState('')
  const { chats, agents, activeChatId, createNewChat, deleteChat } = useChatContext()

  const filteredChats = chats.filter((chat) =>
    chat.title.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const handleCreateNewChat = (e: React.MouseEvent) => {
    e.preventDefault()
    createNewChat()
  }

  return (
    <SidebarGroup className="flex-1 flex flex-col min-h-0">
      <div className="relative px-2 pb-2">
        <Search className="absolute left-4 top-2.5 size-4 text-muted-foreground" />
        <Input
          placeholder="Search chats..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-8"
        />
      </div>
      <div className="flex items-center justify-between pb-2">
        <SidebarGroupLabel>Recent Chats</SidebarGroupLabel>
        <Button
          variant="ghost"
          size="icon"
          className="size-6 mr-1"
          onClick={handleCreateNewChat}
        >
          <Plus className="size-4" />
        </Button>
      </div>
      <SidebarGroupContent className="flex-1 min-h-0">
        <div className="h-full overflow-y-auto">
          <SidebarMenu>
            {filteredChats.map((chat) => (
              <SidebarMenuItem key={chat.id}>
                <div className="group/item relative">
                  <Link href={`/chat/${chat.id}`} className="block">
                    <SidebarMenuButton isActive={activeChatId === chat.id} className="!w-full !pr-9">
                      <MessageSquare className="size-4" />
                      <span className="truncate">{chat.title}</span>
                    </SidebarMenuButton>
                  </Link>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={(e) => {
                      e.preventDefault()
                      e.stopPropagation()
                      deleteChat(chat.id)
                    }}
                    className="absolute right-1 top-1/2 -translate-y-1/2 size-7 opacity-0 group-hover/item:opacity-100 hover:text-destructive hover:bg-sidebar-accent transition-opacity pointer-events-none group-hover/item:pointer-events-auto"
                  >
                    <Trash2 className="size-4" />
                    <span className="sr-only">Delete chat</span>
                  </Button>
                </div>
              </SidebarMenuItem>
            ))}
          </SidebarMenu>
        </div>
      </SidebarGroupContent>
    </SidebarGroup>
  )
}
