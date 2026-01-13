'use client';

import { Input } from '@/components/ui/input';
import { Separator } from '@/components/ui/separator';
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuAction,
  SidebarMenuButton,
  SidebarMenuItem,
} from '@/components/ui/sidebar';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { useChatContext } from '@/contexts/chat-context';
import { Bot, MessageSquare, Plus, Search, Trash2, LayoutGrid, LayoutDashboard, CheckCircle, Zap, Package, BookOpen, Sparkles, ScrollText, ChevronDown } from 'lucide-react';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';

export function AppSidebar() {
  const [searchQuery, setSearchQuery] = useState('');
  const [isNavigationOpen, setIsNavigationOpen] = useState(true);
  const [isConstructionOpen, setIsConstructionOpen] = useState(true);
  const pathname = usePathname();
  const router = useRouter();
  const { chats, agents, activeChatId, createNewChat, deleteChat } = useChatContext();

  const filteredChats = chats.filter((chat) =>
    chat.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleCreateNewChat = (e: React.MouseEvent) => {
    e.preventDefault();
    // Utiliser le premier agent disponible
    const defaultAgent = agents[0]?.id;
    if (defaultAgent) {
      createNewChat(defaultAgent);
    }
  };

  return (
    <Sidebar collapsible="offcanvas">
      <SidebarContent className="flex flex-col">
        {/* Header */}
        <div className="px-6 py-5 flex items-center gap-3">
          <img
            src="/logo.svg"
            alt="Logo"
            width={24}
            height={24}
            className="shrink-0"
          />
          <h2 className="text-base font-bold">Multimodal AI Client</h2>
        </div>

        {/* Navigation principale */}
        <Collapsible open={isNavigationOpen} onOpenChange={setIsNavigationOpen}>
          <SidebarGroup className="flex-shrink-0">
            <CollapsibleTrigger asChild>
              <SidebarGroupLabel className="cursor-pointer hover:bg-sidebar-accent hover:text-sidebar-accent-foreground rounded-md flex items-center justify-between">
                <span>Navigation</span>
                <ChevronDown className={`size-4 transition-transform ${isNavigationOpen ? '' : '-rotate-90'}`} />
              </SidebarGroupLabel>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <SidebarGroupContent>
                <SidebarMenu>
                  <SidebarMenuItem>
                    <Link href="/validation">
                      <SidebarMenuButton isActive={pathname === '/validation'}>
                        <CheckCircle className="size-4" />
                        <span>Validation</span>
                      </SidebarMenuButton>
                    </Link>
                  </SidebarMenuItem>
                  <SidebarMenuItem>
                    <Link href="/automatisations">
                      <SidebarMenuButton isActive={pathname === '/automatisations'}>
                        <Zap className="size-4" />
                        <span>Automatisations</span>
                      </SidebarMenuButton>
                    </Link>
                  </SidebarMenuItem>
                </SidebarMenu>
              </SidebarGroupContent>
            </CollapsibleContent>
          </SidebarGroup>
        </Collapsible>

        {/* Section Construction */}
        <Collapsible open={isConstructionOpen} onOpenChange={setIsConstructionOpen}>
          <SidebarGroup className="flex-shrink-0">
            <CollapsibleTrigger asChild>
              <SidebarGroupLabel className="cursor-pointer hover:bg-sidebar-accent hover:text-sidebar-accent-foreground rounded-md flex items-center justify-between">
                <span>Construction</span>
                <ChevronDown className={`size-4 transition-transform ${isConstructionOpen ? '' : '-rotate-90'}`} />
              </SidebarGroupLabel>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <SidebarGroupContent>
                <SidebarMenu>
                  <SidebarMenuItem>
                    <Link href="/agents">
                      <SidebarMenuButton isActive={pathname === '/agents'}>
                        <Bot className="size-4" />
                        <span>Agents</span>
                      </SidebarMenuButton>
                    </Link>
                  </SidebarMenuItem>
                  <SidebarMenuItem>
                    <Link href="/mcp-tools">
                      <SidebarMenuButton isActive={pathname === '/mcp-tools'}>
                        <Package className="size-4" />
                        <span>MCP et outils</span>
                      </SidebarMenuButton>
                    </Link>
                  </SidebarMenuItem>
                  <SidebarMenuItem>
                    <Link href="/ressources">
                      <SidebarMenuButton isActive={pathname === '/ressources'}>
                        <BookOpen className="size-4" />
                        <span>Ressources</span>
                      </SidebarMenuButton>
                    </Link>
                  </SidebarMenuItem>
                </SidebarMenu>
              </SidebarGroupContent>
            </CollapsibleContent>
          </SidebarGroup>
        </Collapsible>

        <Separator className="my-2" />

        {/* Liste des chats */}
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
                      <SidebarMenuButton
                        isActive={activeChatId === chat.id}
                        onClick={() => router.push(`/chat/${chat.id}`)}
                        className="w-full pr-9"
                      >
                        <MessageSquare className="size-4" />
                        <span className="truncate">{chat.title}</span>
                      </SidebarMenuButton>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          deleteChat(chat.id);
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
      </SidebarContent>
    </Sidebar>
  );
}
